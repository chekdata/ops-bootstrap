def handle_user_info(profile):
    item = {}
    item['name'] = profile.name
    item['id'] = profile.id

    if profile.pic:
        item['pic'] = profile.pic

    if profile.phone:
        item['phone'] = profile.phone

    if profile.desc:
        item['desc'] = profile.desc

    if profile.gender:
        item['gender'] = profile.gender

    if profile.signature:
        item['signature'] = profile.signature

    if profile.app_software_config_version:
        item['app_software_config_version'] = profile.app_software_config_version

    if profile.model_config:
        item['model_config'] = profile.model_config

    if profile.nickname:
        item['nickname'] = profile.nickname

    return item