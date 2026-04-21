1. Run `gcloud auth login` to authenticate
2. Run `./create_policy.sh` to create a new SDP policy
3. Run `./list_data_stores.sh` to list all data stores in default_collection
4. Run `./assign_policy.sh` to assign the SDP policy to data connector
5. Upload a file containing "sensitive data" to sharepoint site
6. Run `./unassign_policy.sh` to unassign the SDP policy from data connector