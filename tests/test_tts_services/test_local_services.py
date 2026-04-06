import unittest

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage


class TestLocalServices(TTSTests):

    def test_windows(self):
        # pytest tests/test_tts_services/ -k test_windows
        service_name = 'Windows'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2

        # pick a random en_US voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'This is the first sentence')

        # pick a random en_US voice with modified rate
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'This is the first sentence', voice_options={'rate': -1})

    def test_espeakng(self):
        service_name = 'ESpeakNg'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} service')
        assert len(service_voices) >= 5

        # pick a random en_US voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'welcome home')

    def test_macos_parse_voice_list(self):
        # pytest tests/test_tts_services/ -k 'TestLocalServices and test_macos_parse_voice_list'
        VOICE_LIST="""
Aasing (Enhanced)   zh_HK    # 你好！我叫阿成。
Agnes               en_US    # Hello! My name is Agnes.
Albert              en_US    # Hello! My name is Albert.
Alex                en_US    # Hello! My name is Alex.
Alice               it_IT    # Ciao! Mi chiamo Alice.
Alice (Enhanced)    it_IT    # Ciao! Mi chiamo Alice.
Allison             en_US    # Hello! My name is Allison.
Allison (Enhanced)  en_US    # Hello! My name is Allison.
Soumya              kn_IN    # Hello! My name is Soumya.
Soumya (Enhanced)   kn_IN    # Hello! My name is Soumya.
Alva                sv_SE    # Hej! Jag heter Alva.
Alva (Enhanced)     sv_SE    # Hej! Jag heter Alva.
Alva (Premium)      sv_SE    # Hej! Jag heter Alva.
Amélie              fr_CA    # Bonjour! Je m’appelle Amélie.
Amélie (Enhanced)   fr_CA    # Bonjour! Je m’appelle Amélie.
Amélie (Premium)    fr_CA    # Bonjour! Je m’appelle Amélie.
Amira               ms_MY    # Hi my name is Amira
Amira (Enhanced)    ms_MY    # Helo! Nama saya Amira.
Ananya              mr_IN    # Hello! My name is Ananya.
Ananya (Enhanced)   mr_IN    # Hello! My name is Ananya.
Angélica (Enhanced) es_MX    # ¡Hola! Me llamo Angélica.
Anna                de_DE    # Hallo! Ich heiße Anna.
Anna (Enhanced)     de_DE    # Hallo! Ich heiße Anna.
Anna (Premium)      de_DE    # Hallo! Ich heiße Anna.
Aude                fr_BE    # Bonjour, je m’appelle Aude.
Aude (Enhanced)     fr_BE    # Bonjour, je m’appelle Aude.
Audrey              fr_FR    # Bonjour, je m’appelle Audrey.
Audrey (Enhanced)   fr_FR    # Bonjour, je m’appelle Audrey.
Audrey (Premium)    fr_FR    # Bonjour, je m’appelle Audrey.
Aurélie             fr_FR    # Bonjour, je m’appelle Aurélie.
Aurélie (Enhanced)  fr_FR    # Bonjour, je m’appelle Aurélie.
Ava                 en_US    # Hello! My name is Ava.
Ava (Enhanced)      en_US    # Hello! My name is Ava.
Ava (Premium)       en_US    # Hello! My name is Ava.
Bad News            en_US    # Hello! My name is Bad News.
Bahh                en_US    # Hello! My name is Bahh.
Bells               en_US    # Hello! My name is Bells.
Binbin              zh_CN    # 你好！我叫彬彬。
Binbin (Enhanced)   zh_CN    # 你好！我叫彬彬。
Bobo (Enhanced)     zh_CN    # 你好！我叫波波。
Boing               en_US    # Hello! My name is Boing.
Bruce               en_US    # Hello! My name is Bruce.
Bubbles             en_US    # Hello! My name is Bubbles.
Carlos              es_CO    # ¡Hola! Me llamo Carlos.
Carlos (Enhanced)   es_CO    # ¡Hola! Me llamo Carlos.
Carmela             gl_ES    # Hello! My name is Carmela.
Carmela (Enhanced)  gl_ES    # Hello! My name is Carmela.
Carmit              he_IL    # שלום, שמי כרמית.
Carmit (Enhanced)   he_IL    # שלום, שמי כרמית.
Catarina            pt_PT    # Olá! Chamo‑me Catarina.
Catarina (Enhanced) pt_PT    # Olá! Chamo‑me Catarina.
Cellos              en_US    # Hello! My name is Cellos.
Cem                 tr_TR    # Merhaba, benim adım Cem.
Cem (Enhanced)      tr_TR    # Merhaba, benim adım Cem.
Chantal             fr_CA    # Bonjour! Je m’appelle Chantal.
Chantal (Enhanced)  fr_CA    # Bonjour! Je m’appelle Chantal.
Claire              nl_NL    # Hallo! Mijn naam is Claire.
Claire (Enhanced)   nl_NL    # Hallo! Mijn naam is Claire.
Damayanti           id_ID    # Halo! Nama saya Damayanti.
Damayanti (Enhanced) id_ID    # Halo! Nama saya Damayanti.
Daniel              en_GB    # Hello! My name is Daniel.
Daniel (Enhanced)   en_GB    # Hello! My name is Daniel.
Daria               bg_BG    # Hello! My name is Daria.
Daria (Enhanced)    bg_BG    # Hello! My name is Daria.
Dariush             fa_IR    # Hello! My name is Dariush.
Dariush (Enhanced)  fa_IR    # Hello! My name is Dariush.
Wobble              en_US    # Hello! My name is Wobble.
Diego               es_AR    # ¡Hola! Me llamo Diego.
Diego (Enhanced)    es_AR    # ¡Hola! Me llamo Diego.
Dongmei (Enhanced)  zh_CN_U_SD@sd=cnln # 你好！我叫冬梅。
Eddy (German (Germany)) de_DE    # Hallo! Ich heiße Eddy.
Eddy (English (UK)) en_GB    # Hello! My name is Eddy.
Eddy (English (US)) en_US    # Hello! My name is Eddy.
Eddy (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Eddy.
Eddy (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Eddy.
Eddy (Finnish (Finland)) fi_FI    # Hei! Nimeni on Eddy.
Eddy (French (Canada)) fr_CA    # Bonjour! Je m’appelle Eddy.
Eddy (French (France)) fr_FR    # Bonjour, je m’appelle Eddy.
Eddy (Italian (Italy)) it_IT    # Ciao! Mi chiamo Eddy.
Eddy (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Eddy.
Ellen               nl_BE    # Hallo! Mijn naam is Ellen.
Ellen (Enhanced)    nl_BE    # Hallo! Mijn naam is Ellen.
Emma                it_IT    # Ciao! Mi chiamo Emma.
Emma (Enhanced)     it_IT    # Ciao! Mi chiamo Emma.
Emma (Premium)      it_IT    # Ciao! Mi chiamo Emma.
Pau                 ca_ES_U_SD@sd=esvc # Hola! Em dic Pau.
Pau (Enhanced)      ca_ES_U_SD@sd=esvc # Hola! Em dic Pau.
Evan                en_US    # Hello! My name is Evan.
Evan (Enhanced)     en_US    # Hello! My name is Evan.
Ewa                 pl_PL    # Witaj, nazywam się Ewa.
Ewa (Enhanced)      pl_PL    # Witaj, nazywam się Ewa.
Ewa (Premium)       pl_PL    # Witaj, nazywam się Ewa.
Panpan              zh_CN_U_SD@sd=cnsc # 你好！我叫盼盼。
Panpan (Premium)    zh_CN_U_SD@sd=cnsc # 你好！我叫盼盼。
Federica            it_IT    # Ciao! Mi chiamo Federica.
Federica (Enhanced) it_IT    # Ciao! Mi chiamo Federica.
Federica (Premium)  it_IT    # Ciao! Mi chiamo Federica.
Felipe              pt_BR    # Olá, meu nome é Felipe.
Felipe (Enhanced)   pt_BR    # Olá, meu nome é Felipe.
Fernanda            pt_BR    # Olá, meu nome é Fernanda.
Fernanda (Enhanced) pt_BR    # Olá, meu nome é Fernanda.
Fiona               en_GB_U_SD@sd=gbsct # Hello! My name is Fiona.
Fiona (Enhanced)    en_GB_U_SD@sd=gbsct # Hello! My name is Fiona.
Flo (German (Germany)) de_DE    # Hallo! Ich heiße Flo.
Flo (English (UK))  en_GB    # Hello! My name is Flo.
Flo (English (US))  en_US    # Hello! My name is Flo.
Flo (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Flo.
Flo (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Flo.
Flo (Finnish (Finland)) fi_FI    # Hei! Nimeni on Flo.
Flo (French (Canada)) fr_CA    # Bonjour! Je m’appelle Flo.
Flo (French (France)) fr_FR    # Bonjour, je m’appelle Flo.
Flo (Italian (Italy)) it_IT    # Ciao! Mi chiamo Flo.
Flo (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Flo.
Francisca           es_CL    # ¡Hola! Me llamo Francisca.
Francisca (Enhanced) es_CL    # ¡Hola! Me llamo Francisca.
Fred                en_US    # Hello! My name is Fred.
Geeta               te_IN    # Hello! My name is Geeta.
Geeta (Enhanced)    te_IN    # Hello! My name is Geeta.
Good News           en_US    # Hello! My name is Good News.
Grandma (German (Germany)) de_DE    # Hallo! Ich heiße Grandma.
Grandma (English (UK)) en_GB    # Hello! My name is Grandma.
Grandma (English (US)) en_US    # Hello! My name is Grandma.
Grandma (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Grandma.
Grandma (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Grandma.
Grandma (Finnish (Finland)) fi_FI    # Hei! Nimeni on Grandma.
Grandma (French (Canada)) fr_CA    # Bonjour! Je m’appelle Grandma.
Grandma (French (France)) fr_FR    # Bonjour, je m’appelle Grandma.
Grandma (Italian (Italy)) it_IT    # Ciao! Mi chiamo Grandma.
Grandma (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Grandma.
Grandpa (German (Germany)) de_DE    # Hallo! Ich heiße Grandpa.
Grandpa (English (UK)) en_GB    # Hello! My name is Grandpa.
Grandpa (English (US)) en_US    # Hello! My name is Grandpa.
Grandpa (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Grandpa.
Grandpa (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Grandpa.
Grandpa (Finnish (Finland)) fi_FI    # Hei! Nimeni on Grandpa.
Grandpa (French (Canada)) fr_CA    # Bonjour! Je m’appelle Grandpa.
Grandpa (French (France)) fr_FR    # Bonjour, je m’appelle Grandpa.
Grandpa (Italian (Italy)) it_IT    # Ciao! Mi chiamo Grandpa.
Grandpa (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Grandpa.
Han (Enhanced)      zh_CN    # 你好！我叫瀚。
Han (Premium)       zh_CN    # 你好！我叫瀚。
Haohao (Enhanced)   zh_CN_U_SD@sd=cnsn # 你好！我叫浩浩。
Henrik              nb_NO    # Hei! Jeg heter Henrik.
Henrik (Enhanced)   nb_NO    # Hei! Jeg heter Henrik.
Jester              en_US    # Hello! My name is Jester.
Ioana               ro_RO    # Salut! Numele meu este Ioana.
Ioana (Enhanced)    ro_RO    # Salut! Numele meu este Ioana.
Isabela             es_AR    # ¡Hola! Me llamo Isabela.
Isabela (Enhanced)  es_AR    # ¡Hola! Me llamo Isabela.
Isha                en_IN    # Hello! My name is Isha.
Isha (Enhanced)     en_IN    # Hello! My name is Isha.
Isha (Premium)      en_IN    # Hello! My name is Isha.
Iveta               cs_CZ    # Ahoj! Já jsem Iveta.
Iveta (Enhanced)    cs_CZ    # Ahoj! Já jsem Iveta.
Jacques             fr_FR    # Bonjour, je m’appelle Jacques.
Jaya                bho_IN   # Hello! My name is Jaya.
Jaya (Enhanced)     bho_IN   # Hello! My name is Jaya.
Jian (Enhanced)     ko_KR    # 안녕하세요. 제 이름은 지안입니다.
Jian (Premium)      ko_KR    # 안녕하세요. 제 이름은 지안입니다.
Joana               pt_PT    # Olá! Chamo‑me Joana.
Joana (Enhanced)    pt_PT    # Olá! Chamo‑me Joana.
Joaquim             pt_PT    # Olá! Chamo‑me Joaquim.
Joaquim (Enhanced)  pt_PT    # Olá! Chamo‑me Joaquim.
Joelle (Enhanced)   en_US    # Hello! My name is Joelle.
Jordi               ca_ES    # Hola! Em dic Jordi.
Jordi (Enhanced)    ca_ES    # Hola! Em dic Jordi.
Jorge               es_ES    # ¡Hola! Me llamo Jorge.
Jorge (Enhanced)    es_ES    # ¡Hola! Me llamo Jorge.
Juan                es_MX    # ¡Hola! Me llamo Juan.
Juan (Enhanced)     es_MX    # ¡Hola! Me llamo Juan.
Junior              en_US    # Hello! My name is Junior.
Kanya               th_TH    # สวัสดี! ฉันชื่อกันยา
Kanya (Enhanced)    th_TH    # สวัสดี! ฉันชื่อกันยา
Karen               en_AU    # Hi my name is Karen
Karen (Enhanced)    en_AU    # Hello! My name is Karen.
Karen (Premium)     en_AU    # Hello! My name is Karen.
Kate                en_GB    # Hello! My name is Kate.
Kate (Enhanced)     en_GB    # Hello! My name is Kate.
Kathy               en_US    # Hello! My name is Kathy.
Katya               ru_RU    # Здравствуйте! Меня зовут Катя.
Katya (Enhanced)    ru_RU    # Здравствуйте! Меня зовут Катя.
Kiyara              hi_IN    # नमस्ते, मेरा नाम कियारा है।
Kiyara (Enhanced)   hi_IN    # नमस्ते, मेरा नाम कियारा है।
Kiyara (Premium)    hi_IN    # नमस्ते, मेरा नाम कियारा है।
Klara               sv_SE    # Hej! Jag heter Klara.
Klara (Enhanced)    sv_SE    # Hej! Jag heter Klara.
Krzysztof           pl_PL    # Witaj, nazywam się Krzysztof.
Krzysztof (Enhanced) pl_PL    # Witaj, nazywam się Krzysztof.
Kyoko               ja_JP    # こんにちは! 私の名前はKyokoです。
Kyoko (Enhanced)    ja_JP    # こんにちは! 私の名前はKyokoです。
Laila               ar_001   # مرحبًا! اسمي ليلى.
Laila (Enhanced)    ar_001   # مرحبًا! اسمي ليلى.
Lana                hr_HR    # Bok, zovem se Lana.
Lana (Enhanced)     hr_HR    # Bok, zovem se Lana.
Lanlan (Enhanced)   zh_CN    # 你好！我叫岚岚。
Laura               sk_SK    # Ahoj, volám sa Laura.
Laura (Enhanced)    sk_SK    # Ahoj, volám sa Laura.
Lee                 en_AU    # Hello! My name is Lee.
Lee (Enhanced)      en_AU    # Hello! My name is Lee.
Lee (Premium)       en_AU    # Hello! My name is Lee.
Lekha               hi_IN    # नमस्ते, मेरा नाम लेखा है।
Lekha (Enhanced)    hi_IN    # नमस्ते, मेरा नाम लेखा है।
Lesya               uk_UA    # Привіт! Мене звуть Леся.
Lesya (Enhanced)    uk_UA    # Привіт! Мене звуть Леся.
Lili                zh_CN    # 你好！我叫莉莉。
Lili (Enhanced)     zh_CN    # 你好！我叫莉莉。
Lili (Premium)      zh_CN    # 你好！我叫莉莉。
Lilian (Enhanced)   zh_CN    # 你好！我叫黎潋。
Lilian (Premium)    zh_CN    # 你好！我叫黎潋。
Linh                vi_VN    # Xin chào! Tên tôi là Linh.
Linh (Enhanced)     vi_VN    # Xin chào! Tên tôi là Linh.
Lisheng (Enhanced)  zh_CN    # 你好！我叫理生。
Luca                it_IT    # Ciao! Mi chiamo Luca.
Luca (Enhanced)     it_IT    # Ciao! Mi chiamo Luca.
Luciana             pt_BR    # Olá, meu nome é Luciana.
Luciana (Enhanced)  pt_BR    # Olá, meu nome é Luciana.
Nannan (Enhanced)   wuu_CN   # 你好！我叫南南。
Majed               ar_001   # مرحبًا! اسمي ماجد.
Majed (Enhanced)    ar_001   # مرحبًا! اسمي ماجد.
Majed (Premium)     ar_001   # مرحبًا! اسمي ماجد.
Magnus              da_DK    # Hej! Jeg hedder Magnus.
Magnus (Enhanced)   da_DK    # Hej! Jeg hedder Magnus.
Jamie               en_GB    # Hello! My name is Jamie.
Jamie (Enhanced)    en_GB    # Hello! My name is Jamie.
Jamie (Premium)     en_GB    # Hello! My name is Jamie.
Mariam              ar_001   # مرحبًا! اسمي مريم.
Mariam (Enhanced)   ar_001   # مرحبًا! اسمي مريم.
Tünde               hu_HU    # Üdvözlöm! A nevem Tünde.
Tünde (Enhanced)    hu_HU    # Üdvözlöm! A nevem Tünde.
Tünde (Premium)     hu_HU    # Üdvözlöm! A nevem Tünde.
Marisol             es_ES    # ¡Hola! Me llamo Marisol.
Marisol (Enhanced)  es_ES    # ¡Hola! Me llamo Marisol.
Markus              de_DE    # Hallo! Ich heiße Markus.
Markus (Enhanced)   de_DE    # Hallo! Ich heiße Markus.
Matilda             en_AU    # Hello! My name is Matilda.
Matilda (Enhanced)  en_AU    # Hello! My name is Matilda.
Matilda (Premium)   en_AU    # Hello! My name is Matilda.
Meijia              zh_TW    # 你好，我叫美佳。
Meijia (Premium)    zh_TW    # 你好，我叫美佳。
Melina              el_GR    # Χαίρετε! Το όνομά μου είναι «Μελίνα».
Melina (Enhanced)   el_GR    # Χαίρετε! Το όνομά μου είναι «Μελίνα».
Milena              ru_RU    # Здравствуйте! Меня зовут Милена.
Milena (Enhanced)   ru_RU    # Здравствуйте! Меня зовут Милена.
Minsu               ko_KR    # 안녕하세요. 제 이름은 민수입니다.
Minsu (Enhanced)    ko_KR    # 안녕하세요. 제 이름은 민수입니다.
Miren               eu_ES    # Hello! My name is Miren.
Miren (Enhanced)    eu_ES    # Hello! My name is Miren.
Moira               en_IE    # Hello! My name is Moira.
Moira (Enhanced)    en_IE    # Hello! My name is Moira.
Mónica              es_ES    # ¡Hola! Me llamo Mónica.
Mónica (Enhanced)   es_ES    # ¡Hola! Me llamo Mónica.
Montse              ca_ES    # Hola! Em dic Montse.
Montse (Enhanced)   ca_ES    # Hola! Em dic Montse.
Narisa (Enhanced)   th_TH    # สวัสดี! ฉันชื่อนาริสา
Nathan              en_US    # Hello! My name is Nathan.
Nathan (Enhanced)   en_US    # Hello! My name is Nathan.
Neel                hi_IN    # नमस्ते, मेरा नाम नील है।
Neel (Enhanced)     hi_IN    # नमस्ते, मेरा नाम नील है।
Nicolas             fr_CA    # Bonjour! Je m’appelle Nicolas.
Nicolas (Enhanced)  fr_CA    # Bonjour! Je m’appelle Nicolas.
Nikos               el_GR    # Χαίρετε! Το όνομά μου είναι «Nikos».
Nikos (Enhanced)    el_GR    # Χαίρετε! Το όνομά μου είναι «Nikos».
Noelle (Enhanced)   en_US    # Hello! My name is Noelle.
Nora                nb_NO    # Hei! Jeg heter Nora.
Nora (Enhanced)     nb_NO    # Hei! Jeg heter Nora.
Suhyun              ko_KR    # 안녕하세요. 제 이름은 수현입니다.
Suhyun (Enhanced)   ko_KR    # 안녕하세요. 제 이름은 수현입니다.
Oliver              en_GB    # Hello! My name is Oliver.
Oliver (Enhanced)   en_GB    # Hello! My name is Oliver.
Onni                fi_FI    # Hei! Nimeni on Onni.
Onni (Enhanced)     fi_FI    # Hei! Nimeni on Onni.
Organ               en_US    # Hello! My name is Organ.
Oskar               sv_SE    # Hej! Jag heter Oskar.
Oskar (Enhanced)    sv_SE    # Hej! Jag heter Oskar.
Otoya               ja_JP    # こんにちは! 私の名前はOtoyaです。
Otoya (Enhanced)    ja_JP    # こんにちは! 私の名前はOtoyaです。
Paola               it_IT    # Ciao! Mi chiamo Paola.
Paola (Enhanced)    it_IT    # Ciao! Mi chiamo Paola.
Paulina             es_MX    # ¡Hola! Me llamo Paulina.
Paulina (Enhanced)  es_MX    # ¡Hola! Me llamo Paulina.
Piya                bn_IN    # Hello! My name is Piya.
Piya (Enhanced)     bn_IN    # Hello! My name is Piya.
Petra               de_DE    # Hallo! Ich heiße Petra.
Petra (Enhanced)    de_DE    # Hallo! Ich heiße Petra.
Petra (Premium)     de_DE    # Hallo! Ich heiße Petra.
Superstar           en_US    # Hello! My name is Superstar.
Ralph               en_US    # Hello! My name is Ralph.
Reed (German (Germany)) de_DE    # Hallo! Ich heiße Reed.
Reed (English (UK)) en_GB    # Hello! My name is Reed.
Reed (English (US)) en_US    # Hello! My name is Reed.
Reed (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Reed.
Reed (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Reed.
Reed (Finnish (Finland)) fi_FI    # Hei! Nimeni on Reed.
Reed (French (Canada)) fr_CA    # Bonjour! Je m’appelle Reed.
Reed (Italian (Italy)) it_IT    # Ciao! Mi chiamo Reed.
Reed (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Reed.
Rishi               en_IN    # Hello! My name is Rishi.
Rishi (Enhanced)    en_IN    # Hello! My name is Rishi.
Rocko (German (Germany)) de_DE    # Hallo! Ich heiße Rocko.
Rocko (English (UK)) en_GB    # Hello! My name is Rocko.
Rocko (English (US)) en_US    # Hello! My name is Rocko.
Rocko (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Rocko.
Rocko (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Rocko.
Rocko (Finnish (Finland)) fi_FI    # Hei! Nimeni on Rocko.
Rocko (French (Canada)) fr_CA    # Bonjour! Je m’appelle Rocko.
Rocko (French (France)) fr_FR    # Bonjour, je m’appelle Rocko.
Rocko (Italian (Italy)) it_IT    # Ciao! Mi chiamo Rocko.
Rocko (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Rocko.
Samantha            en_US    # Hello! My name is Samantha.
Samantha (Enhanced) en_US    # Hello! My name is Samantha.
Sandy (German (Germany)) de_DE    # Hallo! Ich heiße Sandy.
Sandy (English (UK)) en_GB    # Hello! My name is Sandy.
Sandy (English (US)) en_US    # Hello! My name is Sandy.
Sandy (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Sandy.
Sandy (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Sandy.
Sandy (Finnish (Finland)) fi_FI    # Hei! Nimeni on Sandy.
Sandy (French (Canada)) fr_CA    # Bonjour! Je m’appelle Sandy.
Sandy (French (France)) fr_FR    # Bonjour, je m’appelle Sandy.
Sandy (Italian (Italy)) it_IT    # Ciao! Mi chiamo Sandy.
Sandy (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Sandy.
Sangeeta            en_IN    # Hello! My name is Sangeeta.
Sangeeta (Enhanced) en_IN    # Hello! My name is Sangeeta.
Sara                da_DK    # Hej! Jeg hedder Sara.
Sara (Enhanced)     da_DK    # Hej! Jeg hedder Sara.
Satu                fi_FI    # Hei! Nimeni on Satu.
Satu (Enhanced)     fi_FI    # Hei! Nimeni on Satu.
Serena              en_GB    # Hello! My name is Serena.
Serena (Enhanced)   en_GB    # Hello! My name is Serena.
Serena (Premium)    en_GB    # Hello! My name is Serena.
Shanshan (Enhanced) zh_CN    # 你好！我叫珊珊。
Shasha (Enhanced)   zh_CN    # 你好！我叫莎莎。
Shelley (German (Germany)) de_DE    # Hallo! Ich heiße Shelley.
Shelley (English (UK)) en_GB    # Hello! My name is Shelley.
Shelley (English (US)) en_US    # Hello! My name is Shelley.
Shelley (Spanish (Spain)) es_ES    # ¡Hola! Me llamo Shelley.
Shelley (Spanish (Mexico)) es_MX    # ¡Hola! Me llamo Shelley.
Shelley (Finnish (Finland)) fi_FI    # Hei! Nimeni on Shelley.
Shelley (French (Canada)) fr_CA    # Bonjour! Je m’appelle Shelley.
Shelley (French (France)) fr_FR    # Bonjour, je m’appelle Shelley.
Shelley (Italian (Italy)) it_IT    # Ciao! Mi chiamo Shelley.
Shelley (Portuguese (Brazil)) pt_BR    # Olá, meu nome é Shelley.
Sinji               zh_HK    # 你好！我叫善怡。
Sinji (Enhanced)    zh_HK    # 你好！我叫善怡。
Sinji (Premium)     zh_HK    # 你好！我叫善怡。
Soledad             es_CO    # ¡Hola! Me llamo Soledad.
Soledad (Enhanced)  es_CO    # ¡Hola! Me llamo Soledad.
Sora                ko_KR    # 안녕하세요. 제 이름은 소라입니다.
Sora (Enhanced)     ko_KR    # 안녕하세요. 제 이름은 소라입니다.
Stephanie           en_GB    # Hello! My name is Stephanie.
Stephanie (Enhanced) en_GB    # Hello! My name is Stephanie.
Susan               en_US    # Hello! My name is Susan.
Susan (Enhanced)    en_US    # Hello! My name is Susan.
Taotao (Enhanced)   zh_CN    # 你好！我叫陶陶。
Tarik               ar_001   # مرحبًا! اسمي طارق.
Tarik (Enhanced)    ar_001   # مرحبًا! اسمي طارق.
Tessa               en_ZA    # Hello! My name is Tessa.
Tessa (Enhanced)    en_ZA    # Hello! My name is Tessa.
Thomas              fr_FR    # Bonjour, je m’appelle Thomas.
Thomas (Enhanced)   fr_FR    # Bonjour, je m’appelle Thomas.
Tiantian            zh_CN    # 你好！我叫田田。
Tiantian (Enhanced) zh_CN    # 你好！我叫田田。
Tina                sl_SI    # Hello! My name is Tina.
Tina (Enhanced)     sl_SI    # Hello! My name is Tina.
Tingting            zh_CN    # Hi my name is Tingting
Tingting (Enhanced) zh_CN    # 你好！我叫婷婷。
Tom                 en_US    # Hello! My name is Tom.
Tom (Enhanced)      en_US    # Hello! My name is Tom.
Trinoids            en_US    # Hello! My name is Trinoids.
Vani                ta_IN    # Hello! My name is Vani.
Vani (Enhanced)     ta_IN    # Hello! My name is Vani.
Veena               en_IN    # Hello! My name is Veena.
Veena (Enhanced)    en_IN    # Hello! My name is Veena.
Vicki               en_US    # Hello! My name is Vicki.
Victoria            en_US    # Hello! My name is Victoria.
Viktor              de_DE    # Hallo! Ich heiße Viktor.
Viktor (Enhanced)   de_DE    # Hallo! Ich heiße Viktor.
Whisper             en_US    # Hello! My name is Whisper.
Xander              nl_NL    # Hallo! Mijn naam is Xander.
Xander (Enhanced)   nl_NL    # Hallo! Mijn naam is Xander.
Jimena              es_CO    # ¡Hola! Me llamo Jimena.
Jimena (Enhanced)   es_CO    # ¡Hola! Me llamo Jimena.
Yannick             de_DE    # Hallo! Ich heiße Yannick.
Yannick (Enhanced)  de_DE    # Hallo! Ich heiße Yannick.
Yelda               tr_TR    # Merhaba, benim adım Yelda.
Yelda (Enhanced)    tr_TR    # Merhaba, benim adım Yelda.
Yue (Premium)       zh_CN    # 你好！我叫月。
Yuna                ko_KR    # 안녕하세요. 제 이름은 유나입니다.
Yuna (Enhanced)     ko_KR    # 안녕하세요. 제 이름은 유나입니다.
Yuna (Premium)      ko_KR    # 안녕하세요. 제 이름은 유나입니다.
Yuri                ru_RU    # Здравствуйте! Меня зовут Юрий.
Yuri (Enhanced)     ru_RU    # Здравствуйте! Меня зовут Юрий.
Zarvox              en_US    # Hello! My name is Zarvox.
Zoe                 en_US    # Hello! My name is Zoe.
Zoe (Enhanced)      en_US    # Hello! My name is Zoe.
Zoe (Premium)       en_US    # Hello! My name is Zoe.
Zosia               pl_PL    # Hi my name is Zosia
Zosia (Enhanced)    pl_PL    # Witaj, nazywam się Zosia.
Zuzana              cs_CZ    # Hi my name is Zuzana
Zuzana (Enhanced)   cs_CZ    # Ahoj! Já jsem Zuzana.
Zuzana (Premium)    cs_CZ    # Ahoj! Já jsem Zuzana.
Fiona               en-scotland # Hello, my name is Fiona. I am a Scottish-English voice.
"""
        import hypertts_addon.services.service_macos
        macos_service = hypertts_addon.services.service_macos.MacOS()
        voice_list = macos_service.parse_voices(VOICE_LIST)
        self.assertTrue(len(voice_list) > 10)
        # look for voices named Audrey, we should have 3 of them
        audrey_voices = [voice for voice in voice_list if 'Audrey' in voice.name]
        self.assertTrue(len(audrey_voices) == 3)

        audrey_1 = audrey_voices[0]
        self.assertEqual(audrey_1.name, 'Audrey')
        self.assertEqual(audrey_1.audio_languages[0], languages.AudioLanguage.fr_FR)
        self.assertEqual(audrey_1.gender, constants.Gender.Female)
        self.assertEqual(audrey_1.voice_key, {'name': 'Audrey'})
        audrey_2 = audrey_voices[1]
        self.assertEqual(audrey_2.name, 'Audrey (Enhanced)')
        self.assertEqual(audrey_2.voice_key, {'name': 'Audrey (Enhanced)'})
        self.assertEqual(audrey_2.gender, constants.Gender.Female)
        self.assertEqual(audrey_2.audio_languages[0], languages.AudioLanguage.fr_FR)
        audrey_3 = audrey_voices[2]
        self.assertEqual(audrey_3.name, 'Audrey (Premium)')
        self.assertEqual(audrey_3.voice_key, {'name': 'Audrey (Premium)'})
        self.assertEqual(audrey_3.gender, constants.Gender.Female)        
        self.assertEqual(audrey_3.audio_languages[0], languages.AudioLanguage.fr_FR)

        # check Eddy voice, its name should be Eddy, and should be available in fr_FR and fr_CA
        eddy_voices = [voice for voice in voice_list if voice.name == 'Eddy']
        
        eddy_fr_fr = [voice for voice in eddy_voices if voice.audio_languages[0] == languages.AudioLanguage.fr_FR]
        self.assertEqual(len(eddy_fr_fr), 1)
        eddy_french_france_voice = eddy_fr_fr[0]
        self.assertEqual(eddy_french_france_voice.name, 'Eddy')
        self.assertEqual(eddy_french_france_voice.gender, constants.Gender.Male)
        self.assertEqual(eddy_french_france_voice.voice_key, {'name': 'Eddy (French (France))'})
        self.assertEqual(eddy_french_france_voice.audio_languages[0], languages.AudioLanguage.fr_FR)

        eddy_fr_ca = [voice for voice in eddy_voices if voice.audio_languages[0] == languages.AudioLanguage.fr_CA]
        self.assertEqual(len(eddy_fr_ca), 1)
        eddy_french_canada_voice = eddy_fr_ca[0]
        self.assertEqual(eddy_french_canada_voice.name, 'Eddy')
        self.assertEqual(eddy_french_canada_voice.gender, constants.Gender.Male)
        self.assertEqual(eddy_french_canada_voice.voice_key, {'name': 'Eddy (French (Canada))'})
        self.assertEqual(eddy_french_canada_voice.audio_languages[0], languages.AudioLanguage.fr_CA)

        fiona_voices = [voice for voice in voice_list if voice.name == 'Fiona']
        self.assertEqual(len(fiona_voices), 1)
        voice = fiona_voices[0]
        self.assertEqual(voice.gender, constants.Gender.Female)
        self.assertEqual(voice.audio_languages[0], languages.AudioLanguage.en_GB)

    def test_macos(self):
        # pytest tests/test_tts_services/ -k test_macos
        service_name = 'MacOS'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list(service_name)
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 64

        # pick a random en_US voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'this is the first sentence')

        # pick a random en_US voice with modified rate
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, languages.AudioLanguage.en_US, 'this is the first sentence', voice_options={'rate': 170})



class TestLocalServicesCLT(TestLocalServices):
    CONFIG_MODE = 'clt'

