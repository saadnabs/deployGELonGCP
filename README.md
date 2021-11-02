# Deploying Grafana Enterprise Logs on GCP

This script is provided to run through the most common commands required to create a K8s cluster on GCP, create all the necessary service accounts and permissions, and deploy GEL via a helm chart.

## Getting started

### Dependencies
- This script is written in python and expects python version 3+
- The following CLI tools are required for this script:
  - gcloud
  - kubectl
  - gsutil
  - helm
- Grafana Enterprise and Logs licenses are required
    - Grafana Enterprise Logs (save as license-gel.jwt)
    - Grafana Enterprise (save as license-ge.jwt)
    
    - Copy those licenses to your local ./deployGEL/data/licenses folder

#TODO pull variables into a config file for the python script

### Running the script
- The script takes two optional flags
    - -v: version of your deploy, will be used as a unique identifier when deploying all the components
    - -d: when passed, invokes a delete of the deployment with the version identifier

An example run of the script:
    python3.9 deployGEL.py -v 2

- Bear in mind that the script will be interactive in a few different parts, so please keep an eye on it.
- It can take up to #TODO 10 mins to complete

### Outcome of the scipt should be:
- A GCP service account created
- GCP IAM permissions added
- A K8s auto cluster created
- A K8s namespace and service account annotated with the GCP service account
- A helm deployment of GEL
- A deployment of GE

### Finalising the setup
- Follow these following steps after everything is deployed to start sending logs and seeing them in your new GEL instances
#TODO