import subprocess
import tempfile
import os
import sys
import logging

import time
import json
import requests
from typing import List

# Anki imports
import aqt.sound

# Addon imports
from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)

class VoicepeakLocal(service.ServiceBase):
    CONFIG_AI_ENABLE = 'Enable AI Analysis (for Emotion)'
    CONFIG_AI_PROVIDER = 'Service Provider'
    CONFIG_AI_API_KEY = 'API Key'
    CONFIG_AI_BASE_URL = 'API Base URL (Leave empty for default)'
    CONFIG_AI_API_PATH = 'API Path (Leave empty for default)'
    CONFIG_AI_MODEL = 'Model (Required)'
    CONFIG_AI_TEMP = 'Temperature (Leave empty for default 1.0)'
    CONFIG_AI_PROMPT = 'System Prompt (Leave empty for default)'

    CONFIG_REFRESH_VOICES = 'Update Voice List (Toggle Checkbox to Refresh)'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def configuration_options(self):
        return {
            self.CONFIG_REFRESH_VOICES: bool,

            self.CONFIG_AI_PROVIDER: ["OpenAI", "Google Gemini", "Azure OpenAI", "OpenAI Compatible"],
            self.CONFIG_AI_API_KEY: str,
            self.CONFIG_AI_BASE_URL: str,
            self.CONFIG_AI_API_PATH: str,
            self.CONFIG_AI_MODEL: str,
            self.CONFIG_AI_TEMP: str, 
            self.CONFIG_AI_PROMPT: str,
        }
        
    def configure(self, config):
        # Refresh Logic: Only trigger if the user explicitly CHANGED it to True.
        # This prevents passive refreshing when editing other settings.
        # We compare the NEW 'config' with the OLD 'self._config'.
        new_refresh_state = config.get(self.CONFIG_REFRESH_VOICES, False)
        old_refresh_state = self._config.get(self.CONFIG_REFRESH_VOICES, False)
        
        if new_refresh_state and not old_refresh_state:
            try:
                self._refresh_voice_list_cache(config) # Pass new config to write cache into it
                # Reset the flag to False immediately so the next time the user opens config,
                # the checkbox is unchecked. This is cleaner UX.
                config[self.CONFIG_REFRESH_VOICES] = False
                
                # Manual Persistence Hack:
                # The framework likely saves the 'config' state passed from the UI (True) *after* this method returns,
                # overriding our in-memory change to False.
                # To fix this, we try to forcefully update the Addon's global configuration file 
                # (meta.json -> "config") directly, if running inside Anki.
                try:
                    # Attempt to get the addon ID from __file__ path or fallback
                    # Path: .../addons21/111623432/hypertts_addon/services/service_voicepeak_local.py
                    # We need to go up 3 levels to find '111623432'.
                    current_file = os.path.abspath(__file__)
                    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                    addon_id = os.path.basename(addon_dir)
                    
                    # Ensure it looks like an ID (digit)
                    if addon_id.isdigit() and 'aqt' in sys.modules:
                         import aqt
                         mw = aqt.mw
                         # Fetch current full config
                         full_config = mw.addonManager.getConfig(addon_id)
                         if full_config:
                             # Navigate path based on observation:
                             # root -> configuration -> service_config -> VoicepeakLocal
                             service_conf = full_config.get('configuration', {}).get('service_config', {}).get('VoicepeakLocal')
                             if service_conf:
                                 service_conf[self.CONFIG_REFRESH_VOICES] = False
                                 # CRITICAL: Also persist the cached voices we just fetched!
                                 # Otherwise, this force-save might overwrite them with empty/stale data.
                                 if 'cached_voices' in config:
                                     service_conf['cached_voices'] = config['cached_voices']
                                 
                                 # Write back to disk
                                 mw.addonManager.writeConfig(addon_id, full_config)
                                 logger.info(f"Forcefully unchecked '{self.CONFIG_REFRESH_VOICES}' and saved voices in global config.")
                                 
                                 # Update In-Memory Cache (HyperTTS singleton)
                                 # The addon caches the config in 'hypertts_addon.hyper_tts.config'
                                 # If we don't update this, the next open will read stale data.
                                 import hypertts_addon
                                 if hasattr(hypertts_addon, 'hyper_tts'):
                                     hypertts_addon.hyper_tts.config = full_config
                                     logger.info("Updated HyperTTS in-memory config cache.")
                except Exception as e_persist:
                    logger.warning(f"Failed to persist uncheck state to disk: {e_persist}")
            except Exception as e:
                # If it failed, we might want to allow retrying immediately?
                # But letting it fail raises exception.
                raise Exception(f"Failed to refresh voice list: {e}")

        # Update inner config
        self._config = config

        if self.CONFIG_AI_PROVIDER not in self._config:
             self._config[self.CONFIG_AI_PROVIDER] = "OpenAI"
        
        # Default AI settings if not present
        if self.CONFIG_AI_BASE_URL not in self._config:
             self._config[self.CONFIG_AI_BASE_URL] = ""
        if self.CONFIG_AI_API_PATH not in self._config:
             self._config[self.CONFIG_AI_API_PATH] = ""
        if self.CONFIG_AI_MODEL not in self._config:
             self._config[self.CONFIG_AI_MODEL] = ""
        if self.CONFIG_AI_TEMP not in self._config:
             self._config[self.CONFIG_AI_TEMP] = "" 
        if self.CONFIG_AI_PROMPT not in self._config:
             self._config[self.CONFIG_AI_PROMPT] = (
                "You are an emotion rater. "
                "Output ONLY JSON with four integer fields: happy, sad, fun, angry in [0,100]. "
                "Be conservative; neutral ≈ low; ≈ high only for strong explicit cues."
             )
    # Voice options available for this service
    VOICE_OPTIONS = {
        'use_ai_emotion': {'default': 'Disabled', 'label': 'Use AI Emotion', 'type': 'list', 'values': ['Disabled', 'Enabled']},
        # Re-enabled as a functional preset option
        'ai_thinking': {'default': 'False', 'type': 'list', 'values': ['False', 'True'], 'label': 'Deep Thinking'},
        'speed': {'default': 100, 'min': 50, 'max': 200, 'type': 'number_int', 'label': 'Speed'},
        'pitch': {'default': 0, 'min': -300, 'max': 300, 'type': 'number_int', 'label': 'Pitch'},
        'happy': {'default': 0, 'min': 0, 'max': 100, 'type': 'number_int', 'label': 'Happy'},
        'sad': {'default': 0, 'min': 0, 'max': 100, 'type': 'number_int', 'label': 'Sad'},
        'angry': {'default': 0, 'min': 0, 'max': 100, 'type': 'number_int', 'label': 'Angry'},
        'fun': {'default': 0, 'min': 0, 'max': 100, 'type': 'number_int', 'label': 'Fun'},
    }

    def _get_executable_path(self):
        # Check default paths
        if sys.platform == "win32":
            default_path = r"C:\Program Files\VOICEPEAK\voicepeak.exe"
        else:
            default_path = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
            
        if os.path.exists(default_path):
            return default_path
            
        return None

    def _refresh_voice_list_cache(self, config=None):
        target_config = config if config else self._config
        executable_path = self._get_executable_path()
        if not executable_path:
             raise Exception("Voicepeak executable not found at default location.")

        cmd = [executable_path, "--list-narrator"]
        logger.info(f"Refreshing Voice List: {cmd}")
        
        try:
            # 5 second timeout as requested
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', timeout=5)
            lines = result.stdout.strip().splitlines()
            
            cached_voices = []
            for line in lines:
                narrator = line.strip()
                if narrator:
                    cached_voices.append(narrator)
            
            target_config['cached_voices'] = cached_voices
            logger.info(f"Previously cached voices updated: {len(cached_voices)} found.")
            
        except subprocess.TimeoutExpired:
            logger.error("Voicepeak timed out (5s).")
            raise Exception("Voicepeak timed out! The process was killed. Please try refreshing again.")
            
        except Exception as e:
            logger.error(f"Voicepeak refresh failed: {e}")
            raise e

    def _kill_voicepeak(self):
        # Utility to force kill voicepeak processes if they hang
        current_pid = os.getpid()
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "voicepeak.exe"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "voicepeak"], capture_output=True)
        except Exception as e:
            logger.error(f"Failed to kill Voicepeak: {e}")
        except Exception as e:
            logger.error(f"Failed to kill Voicepeak: {e}")

    def _get_ai_emotions(self, text, options=None):
        # 1. Check Options Enable (Global disable removed, rely on options passed)
        if not options:
             return {}
             
        use_ai_val = options.get('use_ai_emotion', 'Disabled')
        if use_ai_val != 'Enabled':
            return {}

        # Get provider local helper
        provider = self._config.get(self.CONFIG_AI_PROVIDER, "OpenAI")

        api_key = self._config.get(self.CONFIG_AI_API_KEY)
        # OpenAI Compatible (Local) might not need a key.
        if not api_key and provider != "OpenAI Compatible":
             raise Exception("AI Emotion enabled but no API Key configured.")

        # Base URL handling
        base_url = self._config.get(self.CONFIG_AI_BASE_URL, "").strip().rstrip('/')
        if not base_url:
            if provider == "OpenAI":
                base_url = "https://api.openai.com"
            elif provider == "Azure OpenAI":
                base_url = "https://RESOURCE_NAME.openai.azure.com"
            elif provider == "Google Gemini":
                base_url = "https://generativelanguage.googleapis.com"
            elif provider == "OpenAI Compatible":
                base_url = "https://your-gateway.com"
        
        # Path handling
        api_path = self._config.get(self.CONFIG_AI_API_PATH, "").strip()
        if not api_path:
            if provider == "OpenAI":
                api_path = "/v1/chat/completions"
            elif provider == "Azure OpenAI":
                api_path = "/openai/deployments/DEPLOYMENT_NAME/responses?api-version=previews"
            elif provider == "Google Gemini":
                api_path = "" # Native API constructs path dynamically
            elif provider == "OpenAI Compatible":
                # Standard OpenAI local servers (Ollama, LM Studio, etc) usually use /v1/chat/completions
                # User config can override this, but unique default is better.
                api_path = "/v1/chat/completions"

        # Ensure path starts with / if not empty and not query
        if api_path and not api_path.startswith('/') and not api_path.startswith('?'): 
             api_path = '/' + api_path
        
        url = base_url + api_path
        
        
        # Model handling - Mandatory
        model = self._config.get(self.CONFIG_AI_MODEL, "").strip()
        if not model:
            raise Exception("AI Model parameter is required. Please check your configuration.")

        # Compatibility fix for Google Gemini if using the "models" endpoint
        # The user requested `v1beta/models`. This endpoint might NOT work with standard OpenAI client payload.
        
        try:
            temp_val = self._config.get(self.CONFIG_AI_TEMP, "").strip()
            if not temp_val:
                temp = 1.0
            else:
                temp = float(temp_val)
        except:
            temp = 1.0
            
        system_prompt = self._config.get(self.CONFIG_AI_PROMPT, "")

        # --- NATIVE GEMINI IMPLEMENTATION ---
        if provider == "Google Gemini":
             # Construct Native URL: base/v1beta/models/{model}:generateContent
             # API Key via header x-goog-api-key
             
             # If api_path is somehow set by user to a full path, usage might vary, 
             # but we assume default empty path means we build it.
             if not api_path:
                 api_path = f"/v1beta/models/{model}:generateContent"
             
             if not api_path.startswith('/'):
                 api_path = '/' + api_path
                 
             url = base_url + api_path
             
             headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
             }
             
             # Native Payload
             # System prompt: typically 2.5/3.0 supports system_instruction, but verify via search?
             # Docs say: generationConfig, contents...
             # We will try standard "contents" with text.
             # To ensure JSON, we use responseMimeType
             
             full_prompt = f"{system_prompt}\n\nUser Input Check: {text}"
             
             payload = {
                 "contents": [{
                     "parts": [{"text": full_prompt}]
                 }],
                 "generationConfig": {
                     "temperature": temp,
                     "responseMimeType": "application/json"
                 }
             }
             
             # Deep Thinking Logic for Gemini (Preset Option)
             # Parse 'True'/'False' string from options, default to False
             thinking_val = options.get('ai_thinking', 'False')
             thinking_enabled = thinking_val == 'True'
             if thinking_enabled:
                 # Toggle ON: High thinking
                 payload['generationConfig']['thinkingConfig'] = { "includeThoughts": True, "thinkingLevel": "HIGH" }
             else:
                 # Toggle OFF: Minimal thinking (for models that support it/enforce it)
                 payload['generationConfig']['thinkingConfig'] = { "includeThoughts": False, "thinkingLevel": "MINIMAL" }

             logger.info(f"Requesting NATIVE Gemini Analysis: {url} model={model} thinking={thinking_enabled}")
             
             try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
             except requests.exceptions.HTTPError as e:
                # Retry without ANY thinking params if 400 (covers unsupported "minimal" or "high")
                if e.response.status_code == 400:
                    logger.warning(f"Gemini 400 Error (Likely unsupported thinking params). Retrying clean... Error: {e.response.text}")
                    # Remove thinkingConfig if present
                    if 'thinkingConfig' in payload['generationConfig']:
                        del payload['generationConfig']['thinkingConfig']
                    # Also try removing snake_case variants just in case previous/other logic added them
                    if 'thinking_config' in payload['generationConfig']:
                         del payload['generationConfig']['thinking_config']
                    
                    try:
                        response = requests.post(url, json=payload, headers=headers, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                    except Exception as e2:
                         raise Exception(f"Gemini Retry Failed: {e2}")
                elif e.response.status_code == 404:
                    error_msg = (
                        f"Gemini Endpoint returned 404. URL: {url}. "
                        f"Check if model '{model}' exists."
                    )
                    raise Exception(error_msg)
                else:
                    raise Exception(f"Gemini Request failed: {e}. Body: {e.response.text}")

             try:
                # Parse Response
                # 1. Combine all parts (Gemini parts are a list)
                parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                all_text = "".join([p.get('text', '') for p in parts])
                
                # 2. Extract Generic JSON candidates
                candidates = []
                decoder = json.JSONDecoder()
                pos = 0
                while pos < len(all_text):
                    # Skip non-brace characters to find next potential start
                    next_brace = all_text.find('{', pos)
                    if next_brace == -1:
                        break
                    
                    try:
                        obj, end_idx = decoder.raw_decode(all_text, next_brace)
                        candidates.append(obj)
                        pos = end_idx
                    except json.JSONDecodeError:
                        # Failed to decode from this brace, advance by 1 to try finding nested or next
                        pos = next_brace + 1
                
                # 3. Filter for valid emotion keys
                emotions = {}
                found_valid = False
                # Iterate candidates (prefer last one? usually final answer is last)
                # But let's check keys.
                required_keys = {'happy', 'sad', 'angry', 'fun'}
                
                for cand in reversed(candidates):
                    if isinstance(cand, dict):
                        # Relaxed check: at least one key matches? or all?
                        # The prompt asks for conservative.
                        # Check strict intersection?
                        if required_keys.intersection(cand.keys()):
                             emotions = cand
                             found_valid = True
                             break
                
                if not found_valid and candidates:
                     # Fallback to last dict if no keys match (maybe keys are capitalized?)
                     # Or just empty.
                     logger.warning(f"No exact emotion keys found in candidates: {candidates}. Using last dict.")
                     if isinstance(candidates[-1], dict):
                         emotions = candidates[-1]

             except (KeyError, IndexError, Exception) as e:
                logger.error(f"Gemini response parsing failed: {data} \nError: {e}")
                raise Exception(f"Failed to parse Gemini JSON response: {e}")
 
             # Validate keys (Cast to int)
             valid_emotions = {}
             for key in ['happy', 'sad', 'angry', 'fun']:
                # Handle potential case-insensitivity or string values?
                val = emotions.get(key)
                if val is None:
                    # Try title case
                    val = emotions.get(key.capitalize())
                
                if val is not None:
                    try:
                        valid_emotions[key] = int(float(val))
                    except:
                        pass
            
             logger.info(f"Gemini Emotions received: {valid_emotions}")
             return valid_emotions

             # (Removed original exception blocks as they are handled in the retry block logic above)

        # --- OPENAI / GENERIC WRAPPER IMPLEMENTATION ---
        else:
             # Standard OpenAI Chat Completion logic
             # If API key is empty (local model), provide a dummy key to prevent malformed header issues.
             # "Bearer " (empty) is sometimes rejected.
             used_api_key = api_key if api_key else "sk-local-dummy"
             
             headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {used_api_key}"
             }
    
             payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": temp,
                "response_format": {"type": "json_object"}
             }
             
             # Deep Thinking Logic for OpenAI (Preset Option)
             # Parse 'True'/'False' string from options, default to False
             thinking_val = options.get('ai_thinking', 'False')
             thinking_enabled = thinking_val == 'True'
             if thinking_enabled:
                 payload["reasoning_effort"] = "high"
             else:
                 payload["reasoning_effort"] = "low"

             logger.info(f"Requesting AI Emotion analysis (OpenAI-compat) for: {text[:50]}...")
             try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
             except requests.exceptions.HTTPError as e:
                 # Retry logic for OpenAI (Catch 400 for unsupported "low" or "high")
                 if e.response.status_code == 400:
                     logger.warning(f"OpenAI 400 Error (Likely unsupported reasoning param). Retrying clean... Body: {e.response.text}")
                     if "reasoning_effort" in payload:
                         del payload["reasoning_effort"]
                     
                     try:
                        response = requests.post(url, json=payload, headers=headers, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                     except requests.exceptions.HTTPError as e2:
                        # 2. If STILL 400, remove response_format (Local/Legacy stuff often fail on this)
                        if e2.response.status_code == 400:
                             logger.warning(f"OpenAI Retry 1 Failed (400). Removing response_format and retrying... Error: {e2.response.text}")
                             if "response_format" in payload:
                                 del payload["response_format"]
                             
                             try:
                                 response = requests.post(url, json=payload, headers=headers, timeout=10)
                                 response.raise_for_status()
                                 data = response.json()
                             except Exception as e3:
                                 raise Exception(f"OpenAI Retry 2 Failed: {e3}. Body: {getattr(e3.response, 'text', '') if hasattr(e3, 'response') else ''}")
                        else:
                             raise Exception(f"OpenAI Retry Failed: {e2}")
                 elif e.response.status_code == 404:
                    error_msg = (
                        f"AI Endpoint returned 404 Not Found. "
                        f"URL: {url}. "
                        f"This likely means the MODEL NAME is incorrect (e.g. '{model}' might not exist) "
                        f"or the endpoint URL is wrong. "
                        f"For Gemini, try using model 'gemini-2.0-flash' or 'gemini-1.5-flash'."
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)
                 else:
                     raise Exception(f"AI Request failed: {e}. Response: {e.response.text}")
             except Exception as e:
                logger.error(f"AI Emotion Analysis failed: {e}")
                raise Exception(f"AI Emotion Analysis failed: {e}")
                
             content = data['choices'][0]['message']['content']
             emotions = json.loads(content)
                
             # Validate keys
             valid_emotions = {}
             for key in ['happy', 'sad', 'angry', 'fun']:
                 if key in emotions and isinstance(emotions[key], (int, float)):
                     valid_emotions[key] = int(emotions[key])
            
             logger.info(f"AI Emotions received: {valid_emotions}")
             return valid_emotions
    def voice_list(self) -> List[voice.TtsVoice_v3]:
        # Read from cache ONLY - configured via "Refresh Voice List" checkbox
        cached_names = self._config.get('cached_voices', [])
        
        voices = []
        for narrator in cached_names:
            if not narrator:
                continue
                
            # Heuristic for gender
            gender = constants.Gender.Female if "Female" in narrator or "Girl" in narrator else constants.Gender.Male
            
            voices.append(voice.build_voice_v3(
                name=narrator,
                gender=gender,
                language=languages.AudioLanguage.ja_JP, 
                service=self,
                voice_key={'id': narrator, 'name': narrator},
                options=self.VOICE_OPTIONS
            ))
            
        return voices

    def get_tts_audio(self, source_text, voice_obj: voice.TtsVoice_v3, options):
        executable_path = self._get_executable_path()
        if not executable_path:
             raise errors.MissingServiceConfiguration(self.name, "executable_path")
        
        # Use tempfile.NamedTemporaryFile to manage files, but we need paths for subprocess and conversion
        # We use delete=False because we need to close the file before subprocess/conversion uses it
        # and then clean up manually.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        
        mp3_path = wav_path.replace(".wav", ".mp3")
        
        narrator = voice_obj.voice_key['name']
        speed = str(options.get('speed', 100))
        pitch = str(options.get('pitch', 0))

        cmd = [
            executable_path,
            "-s", source_text,
            "-n", narrator,
            "-o", wav_path,
            "--speed", speed,
            "--pitch", pitch
        ]
        
        # Add emotions
        emotions = []
        
        # Check if AI Emotion is enabled
        ai_emotions = {}
        if self._config.get(self.CONFIG_AI_API_KEY):
            # Pass options to _get_ai_emotions
            try:
                ai_emotions = self._get_ai_emotions(source_text, options)
            except Exception as e:
                # If AI fails, we might want to fail hard or fallback?
                # Usually we want to know AI failed.
                logger.error(f"AI Emotion failed: {e}")
                raise e

        for emo in ['happy', 'sad', 'angry', 'fun']:
            # AI value takes precedence if available
            if emo in ai_emotions:
                val = ai_emotions[emo]
            else:
                val = options.get(emo, 0)
            
            if val > 0:
                emotions.append(f"{emo}={val}")
        
        if emotions:
            cmd.append("-e")
            cmd.append(",".join(emotions))
        
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"Running Voicepeak command (attempt {attempt + 1}/{max_retries}): {cmd}")
                    subprocess.run(cmd, check=True, capture_output=True, timeout=10)
                    
                    if not os.path.exists(wav_path):
                        raise Exception("Voicepeak did not generate output file")

                    # Convert to MP3 using Anki's utility
                    aqt.sound._encode_mp3(wav_path, mp3_path)
                    
                    if os.path.exists(mp3_path):
                        with open(mp3_path, "rb") as f:
                            audio_data = f.read()
                        return audio_data
                    else:
                        raise Exception("MP3 conversion failed")
                        
                except subprocess.TimeoutExpired as e:
                    logger.warning(f"Voicepeak timed out (attempt {attempt + 1}): {e}")
                    self._kill_voicepeak()
                except subprocess.CalledProcessError as e:
                    stderr_output = e.stderr.decode('utf-8') if e.stderr else str(e)
                    logger.warning(f"Voicepeak execution failed (attempt {attempt + 1}): {stderr_output}")
                    
                    # Check for specific "iconv_open" error or other known crash indicators
                    if "iconv_open" in stderr_output or "supported" in stderr_output: # Loose check for "iconv_open is not supported"
                        self._kill_voicepeak()
                    else:
                        # If it's some other error, we might still want to retry or just raise
                        # The user said "Whenever an error occurs... kill voicepeak background and retry"
                        self._kill_voicepeak()

                except Exception as e:
                    logger.error(f"Voicepeak error (attempt {attempt + 1}): {str(e)}")
                    # General exception, maybe file system related? 
                    # If we suspect Voicepeak might be hanging or causing issues, we can kill it too
                    self._kill_voicepeak()
                
                # Sleep before next attempt
                if attempt < max_retries - 1:
                    time.sleep(1)
            
            # If we reach here, all retries failed
            raise errors.RequestError(source_text, voice_obj, f"Voicepeak failed after {max_retries} attempts.")
        finally:
            # Cleanup both files
            if os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass
            if os.path.exists(mp3_path):
                try:
                    os.unlink(mp3_path)
                except:
                    pass
