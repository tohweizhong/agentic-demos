import sys

with open('terraform/tests/mini_build.tftest.hcl', 'r') as f:
    content = f.read()

bad_line = 'google_model_armor_template.this["request"].filter_config[0].sdp_filter_settings[0].filter_enforcement'
good_line = 'google_model_armor_template.this["request"].filter_config[0].sdp_settings[0].basic_config[0].filter_enforcement'

content = content.replace(bad_line, good_line)

with open('terraform/tests/mini_build.tftest.hcl', 'w') as f:
    f.write(content)
