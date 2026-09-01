from re import sub
import sys
import os
import importlib
import importlib.util
import dataclasses

import typing
import requests
import pprint
import functools
import time


from . import voice as voice_module
from . import service
from . import errors
from . import version
from . import constants
from . import constants_events
from . import config_models
from . import cloudlanguagetools as cloudlanguagetools_module
from . import logging_utils
from . import stats
logger = logging_utils.get_child_logger(__name__)

# don't publish more than X events for a batch uuid
COUNT_BY_BATCH_UUID = {}

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

EXTENSIONS_MODULE_PREFIX = constants.EXTENSIONS_MODULE_PREFIX


@dataclasses.dataclass
class ExtensionLoadError:
    """a third party service which could not be loaded. these are reported to the user rather than
    raised, so that one broken extension doesn't prevent HyperTTS from starting up"""
    source: str
    message: str

    def __str__(self):
        return f'{self.source}: {self.message}'


def find_service_files(directory: typing.Optional[str]) -> typing.List[str]:
    """return the full paths of the service_*.py files directly inside directory"""
    if directory == None or not os.path.isdir(directory):
        return []
    return sorted([
        os.path.join(directory, filename)
        for filename in os.listdir(directory)
        if filename.startswith('service_') and filename.endswith('.py')
    ])


def resolve_extensions_services_directory(extensions_directory: typing.Optional[str]) -> typing.Optional[str]:
    """the user is asked for the anki-hyper-tts-extensions repository directory, which contains the
    service files in a services/ subdirectory. be lenient and also accept a directory which directly
    contains service_*.py files, since users may point at the services/ subdirectory itself, or at an
    extracted zip file. returns None if no service files could be found."""
    if extensions_directory == None:
        return None
    extensions_directory = os.path.expanduser(extensions_directory.strip())
    if len(extensions_directory) == 0:
        return None
    services_subdirectory = os.path.join(extensions_directory, constants.DIR_SERVICES)
    if len(find_service_files(services_subdirectory)) > 0:
        return services_subdirectory
    if len(find_service_files(extensions_directory)) > 0:
        return extensions_directory
    return None

class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory, package_name, allow_test_services,
                 cloudlanguagetools=cloudlanguagetools_module.CloudLanguageTools(),
                 extensions_directory=None):
        self.services_directory = services_directory
        self.package_name = package_name
        self.services = {}
        self.cloudlanguagetools_enabled = False
        self.allow_test_services = allow_test_services
        self.cloudlanguagetools = cloudlanguagetools
        # anki-hyper-tts-extensions repository directory, None when extensions are disabled
        self.extensions_directory = extensions_directory
        # names of the services which were loaded from extensions_directory
        self.extension_service_names = set()
        # extensions which couldn't be loaded, reported to the user at startup
        self.extension_load_errors: typing.List[ExtensionLoadError] = []

    def configure(self, configuration_model, disable_ssl_verification: bool = False) -> bool:
        # will return true if at least one service is enabled
        return_value = False
        hypertts_pro_mode = configuration_model.hypertts_pro_api_key_set()
        for service_name, enabled in configuration_model.get_service_enabled_map().items():
            if not self.service_exists(service_name):
                logger.warning(f'could not find service {service_name}, cannot configure')
                continue
            service = self.get_service(service_name)
            logger.info(f'configuring service {service_name}, hypertts_pro_mode: {hypertts_pro_mode}, clt_enabled: {service.cloudlanguagetools_enabled()}')
            if not (hypertts_pro_mode == True and service.cloudlanguagetools_enabled()):
                service.enabled = enabled
                if enabled:
                    # at least one service enabled
                    return_value = True
                # do we need to set configuration for this service ? only do so if the service is enabled
                if enabled and service_name in configuration_model.get_service_config():
                    service_config = configuration_model.get_service_config()[service_name]
                    service.configure(service_config)
        # if we enable cloudlanguagetools, it may force some services to enabled
        self.cloudlanguagetools.configure(configuration_model, disable_ssl_verification)
        if hypertts_pro_mode:
            self.configure_cloudlanguagetools(configuration_model)
            # all hypertts pro services enabled
            return_value = True
        else:
            self.cloudlanguagetools_enabled = False

        return return_value

    def remove_non_existent_services(self, configuration_model):
        # third party services are only loaded when the extensions directory is enabled and
        # available. their configuration (which includes API keys) must survive a disabled or
        # missing extensions directory, so remember their names and never prune them.
        protected_service_names = self.extension_service_names.union(
            configuration_model.extension_service_names)
        configuration_model.extension_service_names = sorted(protected_service_names)

        def keep_service(service_name):
            return self.service_exists(service_name) or service_name in protected_service_names

        # remove non existent services from the service enabled map
        service_enabled_map = configuration_model.get_service_enabled_map()
        service_list = list(service_enabled_map.keys())
        for service_name in service_list:
            if not keep_service(service_name):
                del service_enabled_map[service_name]
        # do the same thing from the service config map
        service_config_map = configuration_model.get_service_config()
        service_list = list(service_config_map.keys())
        for service_name in service_list:
            if not keep_service(service_name):
                del service_config_map[service_name]
        configuration_model.set_service_enabled_map(service_enabled_map)
        configuration_model.set_service_config(service_config_map)

        return configuration_model

            

    # service discovery
    # =================

    def discover_services(self):
        module_names = []
        for path, dirs, files in os.walk(self.services_directory):
            for filename in files:
                if filename.startswith('service_') and filename.endswith('.py'):
                    module_name = filename.replace('.py', '')        
                    module_names.append(module_name)
        return module_names

    def init_services(self):
        self.import_services()
        self.instantiate_services()
        self.init_extension_services()

    def init_extension_services(self):
        """load third party services from self.extensions_directory. never raises: a broken
        extension must not prevent HyperTTS from starting up"""
        if self.extensions_directory == None:
            return
        services_directory = resolve_extensions_services_directory(self.extensions_directory)
        if services_directory == None:
            logger.warning(f'no extension services found in {self.extensions_directory}')
            self.extension_load_errors.append(ExtensionLoadError(
                self.extensions_directory, 'no service files found in this directory'))
            return
        logger.info(f'loading extension services from {services_directory}')
        # diff the ServiceBase subclasses before/after importing, so that we know which services
        # came from extensions (built-in services are already imported at this point)
        known_subclasses = set(service.ServiceBase.__subclasses__())
        self.import_extension_services(services_directory)
        new_subclasses = [subclass for subclass in service.ServiceBase.__subclasses__()
                          if subclass not in known_subclasses]
        self.instantiate_extension_services(new_subclasses)

    def import_extension_services(self, services_directory):
        service_files = find_service_files(services_directory)
        logger.info(f'discovered {len(service_files)} extension services')
        for file_path in service_files:
            filename = os.path.basename(file_path)
            module_name = EXTENSIONS_MODULE_PREFIX + filename[:-len('.py')]
            logger.info(f'importing extension service {file_path} as {module_name}')
            try:
                # spec_from_file_location sets __file__ on the module, which extension services
                # rely on to locate data files sitting next to them
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                logger.exception(f'could not import extension service {file_path}')
                sys.modules.pop(module_name, None)
                self.extension_load_errors.append(ExtensionLoadError(filename, str(e)))

    def instantiate_extension_services(self, subclasses):
        for subclass in subclasses:
            try:
                subclass_instance = subclass()
            except Exception as e:
                logger.exception(f'could not instantiate extension service {subclass.__name__}')
                self.extension_load_errors.append(ExtensionLoadError(subclass.__name__, str(e)))
                continue
            if subclass_instance.test_service() and self.allow_test_services == False:
                logger.info(f'skipping test service {subclass_instance.name}')
                continue
            if subclass_instance.name in self.services:
                # built-in services take precedence, otherwise an extension could silently shadow a
                # built-in service and inherit its stored configuration (they're keyed by name)
                logger.warning(f'extension service {subclass_instance.name} conflicts with an existing service, skipping')
                self.extension_load_errors.append(ExtensionLoadError(
                    subclass_instance.name, 'a service with this name already exists, extension skipped'))
                continue
            logger.info(f'instantiating extension service {subclass_instance.name}')
            self.services[subclass_instance.name] = subclass_instance
            self.extension_service_names.add(subclass_instance.name)

    def import_services(self):
        module_names = self.discover_services()
        logger.info(f'discovered {len(module_names)} services')
        for module_name in module_names:
            logger.info(f'importing module {module_name}, package_name: {self.package_name}')
            importlib.import_module(f'{self.package_name}.{module_name}')

    def instantiate_services(self):
        for subclass in service.ServiceBase.__subclasses__():
            if subclass.__module__.startswith(EXTENSIONS_MODULE_PREFIX):
                # extension services are handled by instantiate_extension_services. ServiceBase
                # subclasses are process-wide, so without this an extension loaded by one
                # ServiceManager would leak into every other one.
                continue
            subclass_instance = subclass()
            if subclass_instance.test_service() and self.allow_test_services == False:
                logger.info(f'skipping test service {subclass_instance.name}')
                continue
            logger.info(f'instantiating service {subclass_instance.name}')
            self.services[subclass_instance.name] = subclass_instance

    def service_exists(self, service_name):
        return service_name in self.services
    
    def get_service(self, service_name):
        return self.services[service_name]

    def get_all_services(self):
        return list(self.services.values())

    # service configuration
    # =====================

    def configure_cloudlanguagetools(self, configuration: config_models.Configuration):
        logger.info('configure_cloudlanguagetools')
        self.cloudlanguagetools_enabled = True
        # enable all services which are supported by cloud language tools
        for service in self.get_all_services():
            if service.cloudlanguagetools_enabled():
                logger.info(f'enabling {service.name} with cloud language tools')
                service.enabled = True

    def service_configuration_options(self, service_name):
        return self.services[service_name].configuration_options()

    # getting TTS audio and voice list
    # ================================

    def use_cloud_language_tools(self, voice: voice_module.TtsVoice_v3):
        assert isinstance(voice, voice_module.TtsVoice_v3), f"Expected voice to be TtsVoice_v3, got {type(voice).__name__}"
        if self.cloudlanguagetools_enabled:
            service = self.get_service(voice.service)
            if service.cloudlanguagetools_enabled():
                return True
        return False

    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options, audio_request_context):
        logger.debug(f'get_tts_audio for voice: {voice}')
        # assert the type of voice being passed in
        assert isinstance(voice, voice_module.TtsVoice_v3), f"Expected voice to be TtsVoice_v3, got {type(voice).__name__}"
        if hasattr(sys, '_sentry_crash_reporting'):
            return self.get_tts_audio_instrumented(source_text, voice, options, audio_request_context)
        else:
            return self.get_tts_audio_implementation(source_text, voice, options, audio_request_context)

    def get_tts_audio_transcript(self, source_text, voice: voice_module.TtsVoice_v3, options, audio_request_context):
        logger.debug(f'get_tts_audio_transcript for voice: {voice}')
        assert isinstance(voice, voice_module.TtsVoice_v3), f"Expected voice to be TtsVoice_v3, got {type(voice).__name__}"
        if self.use_cloud_language_tools(voice):
            error_message = f'{voice.service}: transcript generation is not supported through Cloud Language Tools'
            raise errors.RequestError(source_text, voice, error_message)
        service_instance = self.services[voice.service]
        return self._get_tts_audio_transcript_service(service_instance, source_text, voice, options)

    def get_tts_audio_instrumented(self, source_text, voice: voice_module.TtsVoice_v3, options, audio_request_context):
        with sentry_sdk.new_scope() as sentry_scope:
            # inside this scope, we can set tags and context which will get unwound when this scope closes
            sentry_scope.set_context("audio_voice", {
                'name': voice.name,
                'voice_key': voice.voice_key,
                'service': voice.service
            })
            sentry_scope.set_context("audio_options", options)
            sentry_scope.set_context('audio_request', {
                'text': source_text
            })
            sentry_scope.set_context("audio_request_context", {
                'reason': audio_request_context.get_audio_request_reason_tag(),
                'batch_uuid': audio_request_context.get_batch_uuid_str(),
                'retry_count': audio_request_context.retry_count,
                'retry_max': audio_request_context.retry_max,
            })
            use_clt = self.use_cloud_language_tools(voice)
            sentry_scope.set_tags({
                'hypertts_pro': use_clt,
                'audio_service': voice.service,
                'audio_request_reason': audio_request_context.audio_request_reason.name,
                'final_attempt': audio_request_context.is_final_attempt()
            })

            metrics_attributes = {
                "service": voice.service,
                'hypertts_pro': use_clt,
                'reason': audio_request_context.get_audio_request_reason_tag()
            }

            transaction_name = f'{voice.service}'
            if use_clt:
                transaction_name = f'cloudlanguagetools_{voice.service}'
            current_txn = sentry_sdk.get_current_scope().transaction
            if current_txn is not None:
                cm = sentry_sdk.start_span(op="audio", name=transaction_name)
            else:
                cm = sentry_sdk.start_transaction(op="audio", name=transaction_name)
            with cm as transaction:
                try:
                    # audio request metrics
                    sentry_sdk.metrics.count(
                        "audio_request",
                        1,
                        attributes=metrics_attributes,
                    )

                    tts_start = time.time()
                    result_audio = self.get_tts_audio_implementation(source_text, voice, options, audio_request_context)
                    tts_duration_ms = (time.time() - tts_start) * 1000

                    # success metrics
                    sentry_sdk.metrics.count(
                        "audio_request_success",
                        1,
                        attributes=metrics_attributes,
                    )

                    sentry_sdk.metrics.distribution(
                        "audio_request_duration",
                        tts_duration_ms,
                        unit="millisecond",
                        attributes=metrics_attributes,
                    )

                    return result_audio
                except Exception as e:
                    sentry_scope.set_tags({
                        'exception_type': type(e).__name__,
                        'error_retryable': getattr(e, 'retryable', None),
                        'is_audio_request_exception': True
                    })
                    sentry_scope.set_context("exception_type", {
                        'exception_type': type(e).__name__,
                        'error_retryable': getattr(e, 'retryable', None)
                    })
                    # group by default fingerprint + service so that the same
                    # exception type from different services creates separate issues
                    sentry_scope.fingerprint = ['{{ default }}', voice.service]
                    # this the only place we capture audio request exceptions
                    sentry_sdk.capture_exception(e)

                    sentry_sdk.metrics.count(
                        "audio_request_failure",
                        1,
                        attributes={**metrics_attributes, 'exception_type': type(e).__name__},
                    )

                    # let the caller handle the exception as well (e.g. for retry logic)
                    raise


    def get_tts_audio_implementation(self, source_text, voice: voice_module.TtsVoice_v3, options, audio_request_context):
        logger.debug(f'get_tts_audio_implementation for voice: {voice}, source_text: {source_text}')
        use_clt = self.use_cloud_language_tools(voice)

        event_count = COUNT_BY_BATCH_UUID.get(audio_request_context.batch_uuid, 0)
        if event_count < constants_events.GENERATE_MAX_EVENTS:
            audio_request_reason_name = audio_request_context.audio_request_reason.name
            stats.send_event_bg(constants_events.EventContext.servicemanager,
                                constants_events.Event.get_tts_audio,
                                None,
                                {
                                    'use_clt': use_clt,
                                    'service_fee': voice.service_fee.name,
                                    'service': voice.service,
                                    'voice_name': voice.name,
                                    'voice_key': voice.voice_key,
                                    '$set': {
                                        f'audio_request_mode_{audio_request_reason_name}': True,
                                    },
                                })
            event_count += 1
            COUNT_BY_BATCH_UUID[audio_request_context.batch_uuid] = event_count

        if use_clt:
            logger.debug(f'voice: {voice}, using cloudlanguagetools')
            return self.cloudlanguagetools.get_tts_audio(source_text, voice, options, audio_request_context)
        else:
            service_instance = self.services[voice.service]
            logger.debug(f'voice: {voice}, using service {service_instance.name}')
            return self._get_tts_audio_service(service_instance, source_text, voice, options)

    # Raises only subclasses of:
    #   PermanentError  – non-retryable
    #   TransientError  – retryable (timeout, unknown)
    def _get_tts_audio_service(self, service_instance, source_text, voice, options):
        try:
            return service_instance.get_tts_audio(source_text, voice, options)
        except errors.HyperTTSError:
            raise
        except requests.exceptions.Timeout as e:
            raise errors.ServiceTimeoutError(source_text, voice, 'HTTP request timed out') from e
        except requests.exceptions.InvalidHeader as e:
            # requests raises InvalidHeader while *preparing* the request
            # (before any network I/O) when a header value contains illegal
            # characters. In practice this means the user pasted a malformed
            # API key into the service configuration — e.g. an OpenAI key with
            # an embedded newline and a trailing "ZAI_API_KEY=..." line ending
            # up in the Authorization header (Sentry ANKI-HYPER-TTS-JR0). The
            # identical request will keep failing until the user fixes the key,
            # so this is a permanent configuration error. Previously it fell
            # through to the generic handler below and was mis-classified as
            # the retryable UnknownServiceError.
            raise errors.ServicePermissionError(source_text, voice,
                f'Invalid credential / request header — check your API key for '
                f'stray whitespace or newlines: {e}') from e
        except requests.exceptions.ConnectionError as e:
            raise errors.ServiceConnectionError(source_text, voice, str(e)) from e
        except Exception as e:
            raise errors.UnknownServiceError(source_text, voice, str(e)) from e

    def _get_tts_audio_transcript_service(self, service_instance, source_text, voice, options):
        try:
            return service_instance.get_tts_audio_transcript(source_text, voice, options)
        except errors.HyperTTSError:
            raise
        except requests.exceptions.Timeout as e:
            raise errors.ServiceTimeoutError(source_text, voice, 'HTTP request timed out') from e
        except requests.exceptions.InvalidHeader as e:
            raise errors.ServicePermissionError(source_text, voice,
                f'Invalid credential / request header — check your API key for '
                f'stray whitespace or newlines: {e}') from e
        except requests.exceptions.ConnectionError as e:
            raise errors.ServiceConnectionError(source_text, voice, str(e)) from e
        except Exception as e:
            raise errors.UnknownServiceError(source_text, voice, str(e)) from e

    def full_voice_list(self, single_service_name=None) -> typing.List[voice_module.TtsVoice_v3]:
        full_list = []
        for service_name, service_instance in self.services.items():
            if single_service_name != None:
                # we only want voices for a particular service
                if service_name != single_service_name:
                    continue
            logger.debug(f'getting voice list for service {service_name}, enabled: {service_instance.enabled}')
            if service_instance.enabled:
                voices = self.get_service_voice_list(service_name)
                logger.debug(f'got {len(voices)} voices from service {service_name}')
                full_list.extend(voices)
        return full_list

    @functools.lru_cache(maxsize=None)
    def get_service_voice_list(self, service_name: str) -> typing.List[voice_module.TtsVoice_v3]:
        service_instance = self.services[service_name]
        voices = service_instance.voice_list()
        return voices


    def deserialize_voice(self, voice_data) -> voice_module.TtsVoice_v3:
        # avoid loading voice list for services we don't need, this is particularly important for ElevenLabsCustom which does
        # an actual query to their API

        # convert voice_data to TtsVoiceId_v3
        voice_id: voice_module.TttsVoiceId_v3 = voice_module.deserialize_voice_id_v3(voice_data)

        voice_list = self.full_voice_list(single_service_name=voice_id.service)
        voice_subset = [voice for voice in voice_list if voice.get_voice_id() == voice_id]
        if len(voice_subset) == 0:
            raise errors.VoiceNotFound(voice_data)
        return voice_subset[0]

    @functools.lru_cache(maxsize=None)
    def locate_voice(self, voice_id: voice_module.TtsVoiceId_v3) -> voice_module.TtsVoice_v3:
        assert isinstance(voice_id, voice_module.TtsVoiceId_v3), f"Expected voice_id to be TtsVoiceId_v3, got {type(voice_id).__name__}"
        # convert from voice_id to actual voice
        voice_list = self.full_voice_list(single_service_name=voice_id.service)
        # logger.debug(pprint.pformat(voice_list))
        voice_subset = [voice for voice in voice_list if voice.get_voice_id() == voice_id]
        if len(voice_subset) == 0:
            logger.warning(f'could not locate voice for voice_id: {voice_id!r}')
            raise errors.VoiceIdNotFound(voice_id)
        return voice_subset[0]
