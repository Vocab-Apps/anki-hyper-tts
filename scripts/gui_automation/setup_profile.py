#!/usr/bin/env python3
"""
Prepare an isolated Anki base folder for GUI automation:

- creates the base folder and a dedicated profile (so the developer's real
  profile is never touched)
- installs HyperTTS as an add-on made of symlinks back into the git checkout, so
  code edits are picked up by simply restarting Anki. meta.json is deliberately
  NOT symlinked: Anki writes add-on config there and we must not clobber the
  developer's local config / api keys.
- installs AnkiConnect (used to inject notes) on a non-default port
- installs the anki_gui_probe add-on (textual widget tree + remote control)

Run through scripts/gui_automation/start_anki.sh rather than directly.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

ANKI_CONNECT_REPO = 'https://github.com/FooSoft/anki-connect.git'

# top level entries of the git checkout which must NOT be linked into the add-on
# folder. meta.json is add-on config written by Anki at runtime.
ADDON_LINK_EXCLUDE = {
    'meta.json',
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.cache',
}


def log(message):
    print(f'[setup_profile] {message}')


def link_hypertts_addon(repo_dir, addons_dir, addon_name):
    addon_dir = os.path.join(addons_dir, addon_name)
    if os.path.islink(addon_dir):
        # an older version of this script symlinked the whole repo
        os.unlink(addon_dir)
    os.makedirs(addon_dir, exist_ok=True)

    for entry in sorted(os.listdir(repo_dir)):
        if entry in ADDON_LINK_EXCLUDE:
            continue
        target = os.path.join(repo_dir, entry)
        link = os.path.join(addon_dir, entry)
        if os.path.islink(link):
            if os.readlink(link) == target:
                continue
            os.unlink(link)
        elif os.path.exists(link):
            # a real file/dir left over, remove it so the link is authoritative
            if os.path.isdir(link):
                shutil.rmtree(link)
            else:
                os.remove(link)
        os.symlink(target, link)

    # remove stale links pointing at entries which no longer exist in the repo
    for entry in sorted(os.listdir(addon_dir)):
        link = os.path.join(addon_dir, entry)
        if os.path.islink(link) and not os.path.exists(os.readlink(link)):
            os.unlink(link)

    log(f'linked HyperTTS from {repo_dir} into {addon_dir}')
    return addon_dir


def write_hypertts_meta(addon_dir, api_key, vocabai_api):
    """seed add-on config so services are usable without going through the GUI"""
    meta_path = os.path.join(addon_dir, 'meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    else:
        meta = {}
    config = meta.setdefault('config', {})
    configuration = config.setdefault('configuration', {})
    if api_key:
        configuration['hypertts_pro_api_key'] = api_key
        configuration['use_vocabai_api'] = vocabai_api
        log('seeded HyperTTS Pro api key into add-on config')
    # never show the welcome/introduction flow in automation
    configuration.setdefault('display_introduction_message', False)
    configuration.setdefault('trial_registration_step', 'finished')
    configuration.setdefault('user_choice_easy_advanced', True)
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)


def install_ankiconnect(cache_dir, addons_dir, port):
    checkout = os.path.join(cache_dir, 'anki-connect')
    if not os.path.isdir(os.path.join(checkout, 'plugin')):
        log(f'cloning AnkiConnect into {checkout}')
        os.makedirs(cache_dir, exist_ok=True)
        subprocess.run(
            ['git', 'clone', '--depth', '1', ANKI_CONNECT_REPO, checkout],
            check=True)
    else:
        log(f'using cached AnkiConnect checkout {checkout}')

    addon_dir = os.path.join(addons_dir, 'AnkiConnect')
    if os.path.isdir(addon_dir) and not os.path.islink(addon_dir):
        shutil.rmtree(addon_dir)
    elif os.path.islink(addon_dir):
        os.unlink(addon_dir)
    shutil.copytree(os.path.join(checkout, 'plugin'), addon_dir)

    config_path = os.path.join(addon_dir, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config['webBindPort'] = port
    config['webBindAddress'] = '127.0.0.1'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
    log(f'installed AnkiConnect on port {port}')


def install_gui_probe(script_dir, addons_dir):
    source = os.path.join(script_dir, 'addons', 'anki_gui_probe')
    addon_dir = os.path.join(addons_dir, 'anki_gui_probe')
    if os.path.islink(addon_dir):
        os.unlink(addon_dir)
    elif os.path.isdir(addon_dir):
        shutil.rmtree(addon_dir)
    os.symlink(source, addon_dir)
    log(f'linked anki_gui_probe from {source}')


def create_profile(base_dir, profile_name):
    # imported here so a missing aqt gives a clear error after argument parsing
    import anki.lang
    from aqt.profiles import ProfileManager

    # ProfileManager translates the default profile name, which needs the i18n
    # backend to be initialized first
    anki.lang.set_lang('en_US')

    profile_manager = ProfileManager(base_dir)
    profile_manager.setupMeta()
    if profile_name not in profile_manager.profiles():
        log(f'creating anki profile [{profile_name}]')
        profile_manager.create(profile_name)
    else:
        log(f'anki profile [{profile_name}] already exists')
    # avoid the language chooser and the first-run flow on startup
    profile_manager.meta['defaultLang'] = 'en_US'
    profile_manager.meta['firstRun'] = False
    profile_manager.load(profile_name)
    profile_manager.profile['syncKey'] = None
    profile_manager.save()
    profile_manager.db.close()


def read_api_key(secrets_file):
    """extract the vocabai api key from a shell secrets file"""
    if not secrets_file or not os.path.exists(secrets_file):
        return None, False
    api_key = None
    vocabai_api = False
    with open(secrets_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('export '):
                continue
            assignment = line[len('export '):]
            if '=' not in assignment:
                continue
            name, value = assignment.split('=', 1)
            value = value.strip().strip('"').strip("'")
            if name == 'ANKI_LANGUAGE_TOOLS_API_KEY':
                api_key = value
            elif name == 'ANKI_LANGUAGE_TOOLS_VOCABAI_API':
                vocabai_api = value.lower() in ('1', 'true', 'yes')
    return api_key, vocabai_api


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True, help='anki base folder')
    parser.add_argument('--profile', required=True, help='anki profile name')
    parser.add_argument('--repo', required=True, help='hypertts git checkout')
    parser.add_argument('--cache-dir', required=True, help='where to cache downloads')
    parser.add_argument('--ankiconnect-port', type=int, default=8766)
    # must match constants.CONFIG_ADDON_NAME: HyperTTS reads its add-on config
    # under this name, and getConfig() returns None for any other folder name
    parser.add_argument('--addon-name', default='anki-hyper-tts')
    parser.add_argument('--secrets-file', default=None)
    args = parser.parse_args()

    addons_dir = os.path.join(args.base, 'addons21')
    os.makedirs(addons_dir, exist_ok=True)

    addon_dir = link_hypertts_addon(args.repo, addons_dir, args.addon_name)
    api_key, vocabai_api = read_api_key(args.secrets_file)
    write_hypertts_meta(addon_dir, api_key, vocabai_api)
    install_ankiconnect(args.cache_dir, addons_dir, args.ankiconnect_port)
    install_gui_probe(os.path.dirname(os.path.realpath(__file__)), addons_dir)
    create_profile(args.base, args.profile)
    log('profile setup complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
