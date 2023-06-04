import sys
import os
import hashlib
import aqt.sound

if os.name == 'nt':
    import comtypes.client  # Importing comtypes.client will make the gen subpackage
    try:
        from comtypes.gen import SpeechLib  # comtypes
    except ImportError:
        # Generate the SpeechLib lib and any associated files
        engine = comtypes.client.CreateObject("SAPI.SpVoice")
        stream = comtypes.client.CreateObject("SAPI.SpFileStream")
        from comtypes.gen import SpeechLib
    import win32com.client


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

LCIDS = {
	"4": "zh_CHS",
	"1025": "ar_SA",
	"1026": "bg_BG",
	"1027": "ca_ES",
	"1028": "zh_TW",
	"1029": "cs_CZ",
	"1030": "da_DK",
	"1031": "de_DE",
	"1032": "el_GR",
	"1033": "en_US",
  	"1034": "es_ES",
	"1035": "fi_FI",
	"1036": "fr_FR",
	"1037": "he_IL",
	"1038": "hu_HU",
	"1039": "is_IS",
	"1040": "it_IT",
	"1041": "ja_JP",
	"1042": "ko_KR",
	"1043": "nl_NL",
	"1044": "nb_NO",
	"1045": "pl_PL",
	"1046": "pt_BR",
	"1047": "rm_CH",
	"1048": "ro_RO",
	"1049": "ru_RU",
	"1050": "hr_HR",
	"1051": "sk_SK",
	"1052": "sq_AL",
	"1053": "sv_SE",
	"1054": "th_TH",
	"1055": "tr_TR",
	"1056": "ur_PK",
	"1057": "id_ID",
	"1058": "uk_UA",
	"1059": "be_BY",
	"1060": "sl_SI",
	"1061": "et_EE",
	"1062": "lv_LV",
	"1063": "lt_LT",
	"1064": "tg_TJ",
	"1065": "fa_IR",
	"1066": "vi_VN",
	"1067": "hy_AM",
	"1069": "eu_ES",
	"1070": "wen_DE",
	"1071": "mk_MK",
	"1074": "tn_ZA",
	"1076": "xh_ZA",
	"1077": "zu_ZA",
	"1078": "af_ZA",
	"1079": "ka_GE",
	"1080": "fo_FO",
	"1081": "hi_IN",
	"1082": "mt_MT",
	"1083": "se_NO",
	"1086": "ms_MY",
	"1087": "kk_KZ",
	"1088": "ky_KG",
	"1089": "sw_KE",
	"1090": "tk_TM",
	"1092": "tt_RU",
	"1093": "bn_IN",
	"1094": "pa_IN",
	"1095": "gu_IN",
	"1096": "or_IN",
	"1097": "ta_IN",
	"1098": "te_IN",
	"1099": "kn_IN",
	"1100": "ml_IN",
	"1101": "as_IN",
	"1102": "mr_IN",
	"1103": "sa_IN",
	"1104": "mn_MN",
	"1105": "bo_CN",
	"1106": "cy_GB",
	"1107": "kh_KH",
	"1108": "lo_LA",
	"1109": "my_MM",
	"1110": "gl_ES",
	"1111": "kok_IN",
	"1114": "syr_SY",
	"1115": "si_LK",
	"1118": "am_ET",
	"1121": "ne_NP",
	"1122": "fy_NL",
	"1123": "ps_AF",
	"1124": "fil_PH",
	"1125": "div_MV",
	"1128": "ha_NG",
	"1130": "yo_NG",
	"1131": "quz_BO",
	"1132": "ns_ZA",
	"1133": "ba_RU",
	"1134": "lb_LU",
	"1135": "kl_GL",
	"1144": "ii_CN",
	"1146": "arn_CL",
	"1148": "moh_CA",
	"1150": "br_FR",
	"1152": "ug_CN",
	"1153": "mi_NZ",
	"1154": "oc_FR",
	"1155": "co_FR",
	"1156": "gsw_FR",
	"1157": "sah_RU",
	"1158": "qut_GT",
	"1159": "rw_RW",
	"1160": "wo_SN",
	"1164": "gbz_AF",
	"2049": "ar_IQ",
	"2052": "zh_CN",
	"2055": "de_CH",
	"2057": "en_GB",
	"2058": "es_MX",
	"2060": "fr_BE",
	"2064": "it_CH",
	"2067": "nl_BE",
	"2068": "nn_NO",
	"2070": "pt_PT",
	"2077": "sv_FI",
	"2080": "ur_IN",
	"2092": "az_AZ",
	"2094": "dsb_DE",
	"2107": "se_SE",
	"2108": "ga_IE",
	"2110": "ms_BN",
	"2115": "uz_UZ",
	"2128": "mn_CN",
	"2129": "bo_BT",
	"2141": "iu_CA",
	"2143": "tmz_DZ",
	"2155": "quz_EC",
	"3073": "ar_EG",
	"3076": "zh_HK",
	"3079": "de_AT",
	"3081": "en_AU",
	"3082": "es_ES",
	"3084": "fr_CA",
	"3098": "sr_SP",
	"3131": "se_FI",
	"3179": "quz_PE",
	"4097": "ar_LY",
	"4100": "zh_SG",
	"4103": "de_LU",
	"4105": "en_CA",
	"4106": "es_GT",
	"4108": "fr_CH",
	"4122": "hr_BA",
	"4155": "smj_NO",
	"5121": "ar_DZ",
	"5124": "zh_MO",
	"5127": "de_LI",
	"5129": "en_NZ",
	"5130": "es_CR",
	"5132": "fr_LU",
	"5179": "smj_SE",
	"6145": "ar_MA",
	"6153": "en_IE",
	"6154": "es_PA",
	"6156": "fr_MC",
	"6203": "sma_NO",
	"7169": "ar_TN",
	"7177": "en_ZA",
	"7178": "es_DO",
	"7194": "sr_BA",
	"7227": "sma_SE",
	"8193": "ar_OM",
	"8201": "en_JA",
	"8202": "es_VE",
	"8218": "bs_BA",
	"8251": "sms_FI",
	"9217": "ar_YE",
	"9225": "en_CB",
	"9226": "es_CO",
	"9275": "smn_FI",
	"10241": "ar_SY",
	"10249": "en_BZ",
	"10250": "es_PE",
	"11265": "ar_JO",
	"11273": "en_TT",
	"11274": "es_AR",
	"12289": "ar_LB",
	"12297": "en_ZW",
	"12298": "es_EC",
	"13313": "ar_KW",
	"13321": "en_PH",
	"13322": "es_CL",
	"14337": "ar_AE",
	"14346": "es_UR",
	"15361": "ar_BH",
	"15370": "es_PY",
	"16385": "ar_QA",
	"16394": "es_BO",
	"17417": "en_MY",
	"17418": "es_SV",
	"18441": "en_IN",
	"18442": "es_HN",
	"19466": "es_NI",
	"20490": "es_PR",
	"21514": "es_US",
	"31748": "zh_CHT"
}


# copied from Anki
def lcid_hex_str_to_lang_codes(hex_codes: str):
    return [
        LCIDS.get(str(int(code, 16)), "unknown") for code in hex_codes.split(";")
    ]

class Windows(service.ServiceBase):
    DEFAULT_RATE = 0
    RATE_MIN = -10
    RATE_MAX = 10

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def voice_list(self):
        try:
            if os.name != 'nt':
                logger.info(f'running on os {os.name}, disabling {self.name} service')
                return []

            result = []
            # https://docs.microsoft.com/en-us/previous-versions/windows/desktop/ms723614(v=vs.85)
            # https://github.com/DeepHorizons/tts/blob/master/tts/sapi.py
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            sapi_voices = speaker.GetVoices()
            for sapi_voice in sapi_voices:
                langs = sapi_voice.GetAttribute("language")
                name = sapi_voice.GetAttribute("name")
                gender = sapi_voice.GetAttribute("gender")
                logger.info(f'processing voice name: [{name}] langs: [{langs}] gender: {gender}')
                langs = lcid_hex_str_to_lang_codes(langs)
                for lang in langs:
                    if lang in languages.AudioLanguage.__members__:
                        audio_language = languages.AudioLanguage[lang]
                        gender_enum = constants.Gender[gender]
                        logger.info(f'sapi_voice: {name} lang: {audio_language} gender: {gender_enum}')
                        options = {
                            'rate': {'default': self.DEFAULT_RATE, 'max': self.RATE_MAX, 'min': self.RATE_MIN, 'type': 'number_int'}
                        }
                        result.append(voice.Voice(name, gender_enum, audio_language, self, name, options))
                    else:
                        logger.error(f'unknown language: {lang}, could not process voice [{name}]')

            return result

        except Exception as e:
            logger.error(f'could not get voicelist: {e}', exc_info=True)

        return []

    def get_sapi_voice_by_name(self, voice_name):
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        sapi_voices = speaker.GetVoices()
        for sapi_voice in sapi_voices:
            current_name = sapi_voice.GetAttribute("name")
            if current_name == voice_name:
                return sapi_voice
        raise Exception(f'could not find voice with name {voice_name}')

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        logger.info(f'getting audio with voice {voice}')
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # for some reason only filename is accepted by sapi
        combined_data = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'options': options
        }
        file_hash = hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()        

        # python/windows somehow doesn't handle temporary files. create files in %TEMP% instead, 
        # the user should have write access to that location.
        temp_dir = os.environ['TEMP']
        filename_wav = f'hypertts-{file_hash}.wav'
        filename_mp3 = f'hypertts-{file_hash}.mp3'
        
        full_path_wav = os.path.join(temp_dir, filename_wav)
        full_path_mp3 = os.path.join(temp_dir, filename_mp3)

        logger.debug(f'writing to file {full_path_wav}')

        speaker.Voice = self.get_sapi_voice_by_name(voice.voice_key)
        speaker.Rate = options.get('rate', self.DEFAULT_RATE)

        logger.debug(f'opening stream')
        stream = win32com.client.Dispatch('SAPI.SPFileStream')
        stream.Open(full_path_wav, comtypes.gen.SpeechLib.SSFMCreateForWrite)
        temp_stream = speaker.AudioOutputStream
        speaker.AudioOutputStream = stream
        speaker.Speak(source_text)
        speaker.AudioOutputStream = temp_stream
        stream.close()

        logger.debug(f'closing stream')
        
        # convert wav to mp3
        logger.debug(f'converting from {full_path_wav} to {full_path_mp3}')
        aqt.sound._encode_mp3(full_path_wav, full_path_mp3)

        # read filename contents
        f = open(full_path_mp3, 'rb')
        content = f.read()
        f.close()

        # remove temporary files
        # note: the conversion process seems to have removed the original wav file
        os.remove(full_path_mp3)

        return content

