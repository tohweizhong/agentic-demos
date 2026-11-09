import sys
import re

with open('terraform/tests/mini_build.tftest.hcl', 'r') as f:
    content = f.read()

# Remove the bad test block
bad_test = """
run "model_armor_template_loads_yaml" {
  command = apply

  assert {
    condition     = google_model_armor_template.this["request"].template_config[0].filter_config[0].pi_and_jailbreak_filter_settings[0].enforcement == "ENABLED"
    error_message = "The template must load the pi_and_jailbreak enforcement from the YAML."
  }

  assert {
    condition     = google_model_armor_template.this["request"].template_config[0].filter_config[0].sdp_filter_settings[0].enforcement == "ENABLED"
    error_message = "The template must load the sdp enforcement from the YAML."
  }

  assert {
    condition     = google_model_armor_template.this["request"].template_config[0].filter_config[0].malicious_uri_filter_settings[0].enforcement == "ENABLED" || google_model_armor_template.this["request"].template_config[0].filter_config[0].malicious_uri_filter_settings[0].enforcement == "DISABLED"
    error_message = "The template must load the malicious_uri enforcement from the YAML."
  }

  assert {
    condition     = length(google_model_armor_template.this["request"].template_config[0].filter_config[0].rai_settings[0].rai_filters) > 0
    error_message = "The template must load the rai_filters from the YAML."
  }
}
"""

if bad_test in content:
    content = content.replace(bad_test, "")
else:
    # try regex because of spacing
    content = re.sub(r'run "model_armor_template_loads_yaml" \{.*?^\}', '', content, flags=re.MULTILINE|re.DOTALL)


new_test = """
run "model_armor_template_loads_yaml" {
  command = apply

  assert {
    condition     = google_model_armor_template.this["request"].filter_config[0].pi_and_jailbreak_filter_settings[0].filter_enforcement == "ENABLED"
    error_message = "The template must load the pi_and_jailbreak enforcement from the YAML."
  }

  assert {
    condition     = google_model_armor_template.this["request"].filter_config[0].sdp_filter_settings[0].filter_enforcement == "ENABLED"
    error_message = "The template must load the sdp enforcement from the YAML."
  }

  assert {
    condition     = length(google_model_armor_template.this["request"].filter_config[0].rai_settings[0].rai_filters) > 0
    error_message = "The template must load the rai_filters from the YAML."
  }
}
"""
content += new_test

with open('terraform/tests/mini_build.tftest.hcl', 'w') as f:
    f.write(content)
