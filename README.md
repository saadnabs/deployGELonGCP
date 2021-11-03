# Table of Contents
- [Table of Contents](#table-of-contents)
- [Deploying Grafana Enterprise Logs on GCP](#deploying-grafana-enterprise-logs-on-gcp)
  - [Getting started](#getting-started)
    - [Dependencies](#dependencies)
    - [Setting up a deployment environment](#setting-up-a-deployment-environment)
    - [Running the script](#running-the-script)
    - [Known Issues](#known-issues)
    - [Outcome of the scipt should be](#outcome-of-the-scipt-should-be)
    - [Finalising the setup](#finalising-the-setup)
      - [Create Instance](#create-instance)
      - [Create reader access policy and token](#create-reader-access-policy-and-token)
      - [Install PromTail](#install-promtail)

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
sudo apt install python3
```
- Confirm gcloud / gsutil are already installed
- Initialise gcloud to your project by following the cli instructions
```
gcloud init
```
- Install kubectl, [instructions](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
```
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client
```
- Install helm, [instructions](https://helm.sh/docs/intro/install/)
```
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
helm version
```
- Upload licenses to GCE instance - [instructions](https://cloud.google.com/compute/docs/instances/transfer-files)
  - And move them into the correct folder (deployGELonGCP/data/licenses)
  - Make sure to have a license with "Cluster Name" set to $PREFIX-cluster
- Install git
```
sudo apt-get install git
git --version
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

An example run of the script, from within the deployGELonGCP folder:

```
python3.9 deployGEL.py -v 2 -p nabeel
```

### Known Issues
Nov 3, 2021
None identified at the moment.

### Outcome of the scipt should be
- A GCP service account created
- GCP IAM permissions added
- A K8s auto cluster created
- A K8s namespace and service account annotated with the GCP service account
- A helm deployment of GEL
- A deployment of GE

### Finalising the setup
Follow these steps after everything is deployed to start sending logs and seeing them in your new GEL instances
- Log in to your Grafana Enterprise instance at http://$external-ip:3000/login as provided by the script
- Go to Stats & licensing page
- And upload the Grafana Enterprise license

- Set up the Grafana Enterprise Logs plugin following these [instructions](https://grafana.com/docs/enterprise-logs/latest/setup/grafana-plugin/), getting the API Settings by doing the following
  - In K9s, type :service, find the nabeel-gel-enterprise-logs-gateway service’s Cluster IP and copy that or use the service name.
  - Get the token from the tokengen job as done previously

- Create the Logs instance, data source and PromTail access policies (customised these [instructions](https://grafana.com/docs/enterprise-logs/latest/instance/))

#### Create Instance
- Go to “Grafana Enterprise Logs” → Instances
- Click “Create Instance” with the following settings:
  - Display name: $gelInstanceName
  - Cluster: $kubeClusterName

#### Create reader access policy and token
- Go to the “Access Policies” tab and click “Create access policy” with the following settings:
  - Display name: demo reader
  - Scope: logs:read
  - Instances: $gelInstanceName 
- Click the “Add token” for the new policy created and use the following settings:
  - Display name: reader token
  - Expiration date: <you can leave this blank>
- In the “Token successfully added!” dialog, click the “Create a datasource” button 
- Once created, click on the “Data source settings” link, click “Save & Test” at the bottom to confirm the data source works correctly.
- Go back to the “Grafana Enterprise Logs” → “Access policies”
- Click “Create access policy” with the following settings:
  - Display name: demo writer
  - Scope: logs:write
  - Instances: $gelInstanceName
- Click the “Add token” for the new policy created and use the following settings:
  - Display name: writer token
  - Expiration date: <you can leave this blank>
- In the “Token successfully added!” dialog, click the “Copy to clipboard” button to save the Token for use with Promtail
  - $gelWriterToken, e.g. ZGVtbydsdgl0ZXItd3JpdGVyLXRva2Vu323sds5vOjMyQEAsMzE0NXQ1OFE4QDp9MA==

#### Install PromTail

- Install promtail local using a binary you can download from here
  - Using the promtail-config-template.yaml, run promtail after modifying all the variables prefixed with $
    - $PROMTAIL-DATA-LOCATION, e.g a local directory that promtail can write to
    - $GEL-GATEWAY-URL, e.g the TODO URL to your GEL gateway (use port-forwarding and localhost as a simple solution)
    - $GEL-INSTANCE-INTERNAL-NAME, e.g the internal name of the GEL instance
    - $GEL-INSTANCE-ACCESSPOLICY-TOKEN, e.g token taken from the access policy for writing
    - $HOSTNAME, e.g mymachine or node1, the host name of the machine sending the logs
  ```
  ./promtail-darwin-amd64 -config.file=~/$deployGEL/promtail-config.yaml
  ```
- Click “Explore” on the left menu bar, select the data source at the top to be the GEL data source we added previously and click on the “Log browser” so you see the logs that are coming through, select one of the labels and values, then click “Show logs”
