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

### Setting up a deployment environment
- Create a default VM instance (Linux) in Google Cloud, allow http/https traffic, and connect via SSH
- Install python
```
apt install python3
```
- Confirm gcloud / gsutil are already installed
- Initialise gcloud to your project by following the cli instructions
```
gcloud init
```
- Install kubectl, [instructions](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
- Install helm, [instructions](https://helm.sh/docs/intro/install/)
- Upload licenses to GCE instance - [instructions](https://cloud.google.com/compute/docs/instances/transfer-files)
- Install git
```
sudo apt-get install git
```
- Download the deployGEL github repo
```
git clone https://github.com/saadnabs/deployGELonGCP.git
```

### Running the script
- The script takes two optional flags
    - -v: version of your deploy, will be used as a unique identifier when deploying all the components
    - -d: when passed, invokes a delete of the deployment with the version identifier
    - -p: prefix used for all the component names deployed (can be your username, keep it short though others length limits will be hit)

- Bear in mind that the script will be interactive in a few different parts, so please keep an eye on it.
- It can take up to #TODO 10 mins to complete

An example run of the script:

```
python3.9 deployGEL.py -v 2 -p nabeel
```

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