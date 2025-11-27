https://google.github.io/adk-docs/get-started/python/#installation
python3 -m venv .venv
source .venv/bin/activate
pip install google-adk
adk create my_agent


https://google.github.io/adk-docs/deploy/cloud-run/#adk-cli
gcloud auth login
gcloud config set project weizhong-project03
(gcloud auth application-default set-quota-project weizhong-project03)
source ./set_vars.sh

adk deploy cloud_run \
--project=$GOOGLE_CLOUD_PROJECT \
--region=$GOOGLE_CLOUD_LOCATION \
--service_name=$SERVICE_NAME \
--app_name=$APP_NAME \
--with_ui \
$AGENT_PATH

allow-unauthenticated: y
