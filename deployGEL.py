#TODO try removing the dev plugin from grafana-enterprise-template.yaml

import os
import re
import argparse
import time
import sys

import subprocess
from pathlib import Path

#Argument parsing from the command line
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version",dest ="version", default="1", help="The version to use in the deployment")
parser.add_argument('-d', action='store_true', help='Delete action to undertake')

#TODO change default from Nabeel eventually
parser.add_argument("-p", "--prefix",dest ="username", default="nabeel", help="The prefix to use across all the components deployed")
args = parser.parse_args()

version = "v" + args.version
delete = args.d
username = args.username

#print(username)

def output(msg, isHeader=False):
    if (isHeader):
        print("\n************************")
        print(msg)
        print("************************\n")
    else:
        print("--> " + msg)

def timeFunc(func):
    startTime = time.time()
    func()
    endTime = time.time()
    print("\n------------------------------------------------")
    output(func.__name__ + " time elapsed: " + str((endTime - startTime)))

def runAndShowCmd(cmd):
    output(cmd)
    os.system(cmd)

def getGCPServiceAccountId():
    #Get the GCP service account ID
    stream = os.popen('gcloud iam service-accounts list | grep ' + username)
    cmdOut = stream.read()

    match = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', cmdOut)

    if (match):
        return match[0]
    else:
        output("Did not find service account name listed for search criteria [" + username + "]")
        return ""

# def getConfig():
#     import json

#     with open("config.json") as json_data_file:
#         data = json.load(json_data_file)
#     print(data)

# getConfig()

#Variables defined for use throughout
kubeClusterName = username + "-cluster"#-" + version #removing version to not have to update license every time
kubeNamespace = username + "-gel-" + version
kubeServiceAccountName = username + "-sa-" + version

gcpProjectId = "solutions-engineering-248511"
gcpRegion = "europe-west1"
gcpBucketName = username + "-bucket-" + version
gcpKubernetesClusterName = username + "-gel-" + version
gcpServiceAccountName = username + "-se-offsite-" + version
gcpServiceAccountId = getGCPServiceAccountId()

helmReleaseName = username + "-gel-release-" + version
helmGrafanaRepo = "https://grafana.github.io/helm-charts"
helmFolder = "helm-charts"
helmPath= helmFolder + "/charts"

gelGatewayIngress = "gel-gateway-ingress"

#Get the working directory and the helm directory
stream = os.popen('pwd')
deployGELFolder = stream.read().replace("\n", "")
output("Current working directory: " + deployGELFolder)
lastSlashIndex = deployGELFolder.rfind("/")
helmPath = deployGELFolder[0:lastSlashIndex + 1] + helmPath
helmFolder = deployGELFolder[0:lastSlashIndex + 1] + helmFolder
output("Helm charts working directory: " + helmPath)
output("Helm root folder: " + helmFolder)

gcpServiceAccountId = getGCPServiceAccountId()

deployLicenseFolder = deployGELFolder + "/data/licenses"

tokenGenToken = ""

def createYamlFromTemplate(templateName, replaceDict):

    fileName = templateName[0:templateName.find("-template")]
    
    #Modify the overrides variables
    #template file
    fin = open(deployGELFolder + "/" + templateName + ".yaml", "rt")
    #output file to write the result to
    fout = open(deployGELFolder + "/" + fileName + ".yaml", "wt")
    
    #for each line in the template file
    for line in fin:
        for key in replaceDict:
            #read replace the string and write to output file
            line = line.replace('$' + key, replaceDict[key])
        fout.write(line)
    #close template and output files
    fin.close()
    fout.close()

def cleanUpInstall():

    output("Clean up install...", True)
    startTime = time.time()
    
    output("Removing GEL")
    p = subprocess.Popen("helm uninstall " + helmReleaseName + " --namespace " + kubeNamespace, cwd=helmPath, shell=True)
    p.wait()

    output("Removing Grafana Enterprise")
    p = subprocess.Popen("kubectl delete -f " + deployGELFolder + "/grafana-enterprise.yaml --namespace " + kubeNamespace, shell=True)
    p.wait()

    output("Removing GEL ingress")
    p = subprocess.Popen("kubectl delete ingress " + gelGatewayIngress + " --namespace " + kubeNamespace, shell=True)
    p.wait()

    output("Removing K8s SA")
    p = subprocess.Popen("kubectl delete serviceaccounts " + kubeServiceAccountName + " --namespace " + kubeNamespace, shell=True)
    p.wait()

    output("Removing K8s namespace")
    runAndShowCmd("kubectl delete namespace " + kubeNamespace)
    
    #Delete storage bucket
    output("Removing GCS bucket")
    runAndShowCmd("gsutil -m rm -r gs://" + gcpBucketName)

    gcpServiceAccountId = gcpServiceAccountName + "@solutions-engineering-248511.iam.gserviceaccount.com"

    #Remove the GCP service account permission
    output("Removing IAM permissions")
    
    #Get the current policy
    runAndShowCmd("gcloud projects get-iam-policy " + gcpProjectId + " --format json > " + deployGELFolder + "/data/policy-orig.json")
    
    fin = open(deployGELFolder + "/data/policy-orig.json", "rt")
    #output file to write the result to
    fout = open(deployGELFolder + "/data/policy-new.json", "wt")
    #for each line in the template file
    for line in fin:
        #read replace each instance of the serviceaccountID and write to output file
        line = line.replace('"serviceAccount:' + gcpServiceAccountId + '",\n', "")
        fout.write(line)
    #close template and output files
    fin.close()
    fout.close()

    #Update the policy
    runAndShowCmd("gcloud projects set-iam-policy " + gcpProjectId + " " + deployGELFolder + "/data/policy-new.json")
    runAndShowCmd("gcloud iam service-accounts remove-iam-policy-binding " + gcpServiceAccountId + " --member=serviceAccount:" + gcpProjectId + ".svc.id.goog[" + kubeNamespace + "/" + kubeServiceAccountName + "] --role=roles/iam.workloadIdentityUser")

    #Remove the GCP service account
    output("Removing IAM Service Account")
    runAndShowCmd("gcloud iam service-accounts delete " + gcpServiceAccountId)

    output("Removing K8s cluster")
    runAndShowCmd("gcloud container clusters delete " + gcpKubernetesClusterName + " --region " + gcpRegion)

    os.remove(deployGELFolder + "/data/policy-new.json")
    os.remove(deployGELFolder + "/data/policy-orig.json")
    
    endTime = time.time()
    output(cleanUpInstall.__name__ + " time elapsed: " + str((endTime - startTime)))
    quit()

def checkDependencies():
    #List dependencies
    deps = """--> gcloud
    --> kubectl
    --> gsutil
    --> helm
    """
    output("Before you start, please bear in mind that the following CLI packages are depended upon by this python script:", True)
    print(deps)

    output("Go to https://admin.grafana.com to create Grafana licenses for:")
    output("--> Grafana Enterprise Logs (save as license-gel.jwt)")
    output("--> Grafana Enterprise (save as license-ge.jwt)")
    output("Copy those licenses to your local ./" + deployGELFolder + "/data/licenses folder")

    input("\nPressing Enter confirms that you have the above tools. \nOtherwise, break out of the command and install the required tools.\n")

def createK8sCluster():
    output("Deploying K8s cluster on GCP", True)
    #Create GCP K8s cluster (takes a while), don't wait for result of command
    runAndShowCmd("gcloud beta container --project '" + gcpProjectId +"' clusters create-auto '" + gcpKubernetesClusterName \
        + "' --region '" + gcpRegion + "' --release-channel regular")  #--network "projects/solutions-engineering-248511/global/networks/default" --subnetwork "projects/solutions-engineering-248511/regions/us-central1/subnetworks/default" --cluster-ipv4-cidr "/17" --services-ipv4-cidr "/22"")
    #TODO takes a long time, can i not block on it

def createGCPServiceAccount():
    output("Creating GCPservice account", True)

    #Create GCP service account
    runAndShowCmd("gcloud iam service-accounts create " + gcpServiceAccountName + " --description='Used for GEL deployment' --display-name='" + gcpServiceAccountName + "'")

    global gcpServiceAccountId
    gcpServiceAccountId = getGCPServiceAccountId()

    count = 0
    while (gcpServiceAccountId == ""):
        time.sleep(2)
        gcpServiceAccountId = getGCPServiceAccountId()
        count = count + 1

        if (count > 10):
            output("Timed out waiting " + str(count * 2) + " seconds for service account to show up in IAM lists")
            quit()
        else:
            output("Waited " + str(count * 2) + " seconds for the service account, hasn't shown up yet")

    output("printing gcpServiceAccountID: " + gcpServiceAccountId)
    
def createK8sServiceAccountsAndConnectToGCP():

    global gcpServiceAccountId
    output("Creating K8s Service Accounts and connect to GCP", True)
    runAndShowCmd("gcloud container clusters get-credentials " + gcpKubernetesClusterName + " --region " + gcpRegion + " --project " + gcpProjectId)

    runAndShowCmd("kubectl create namespace " + kubeNamespace)

    runAndShowCmd("kubectl create serviceaccount " + kubeServiceAccountName + " --namespace " + kubeNamespace)

    output("\nSelect option (3) below when requested\n")
    
    #This creates the IAM bindings for the Service Account
    runAndShowCmd("gcloud projects add-iam-policy-binding " + gcpProjectId + " --member 'serviceAccount:" + gcpServiceAccountId + "' --role roles/owner")
    #TODO do i need this? 
    runAndShowCmd("gcloud projects add-iam-policy-binding " + gcpProjectId + " --member 'serviceAccount:" + gcpServiceAccountId + "' --role roles/editor")
    runAndShowCmd("gcloud projects add-iam-policy-binding " + gcpProjectId + " --member 'serviceAccount:" + gcpServiceAccountId + "' --role roles/iam.serviceAccountTokenCreator")
    
    runAndShowCmd("gcloud projects add-iam-policy-binding " + gcpProjectId + " --member 'serviceAccount:" + gcpServiceAccountId + "' --role roles/storage.admin")
    
    runAndShowCmd("gcloud projects add-iam-policy-binding " + gcpProjectId + " --member 'serviceAccount:" + gcpServiceAccountId + "' --role roles/iam.workloadIdentityUser")

    runAndShowCmd("gcloud iam service-accounts add-iam-policy-binding " + gcpServiceAccountId + " --role roles/iam.workloadIdentityUser --member 'serviceAccount:" + gcpProjectId + ".svc.id.goog[" + kubeNamespace + "/" + kubeServiceAccountName + "]'")
    
    runAndShowCmd("kubectl annotate serviceaccounts " + kubeServiceAccountName + " --namespace " + kubeNamespace + " iam.gke.io/gcp-service-account=" + gcpServiceAccountId + " --overwrite")  #gcpProjectId + ".svc.id.goog --overwrite")
    
def createGCPBucket():
    output("Creating GCP storage bucket", True)
    runAndShowCmd("gsutil mb -p " + gcpProjectId + " -c STANDARD -l " + gcpRegion + " -b on gs://" + gcpBucketName)

def setupHelm():
    output("Setting up Helm", True)
    Path(helmFolder).mkdir(parents=True, exist_ok=True)

    runAndShowCmd("git clone https://github.com/grafana/helm-charts.git " + helmFolder)

    p = subprocess.Popen(["helm", "repo", "add", "grafana", helmGrafanaRepo], cwd=helmPath)
    p.wait()

    p = subprocess.Popen(["helm", "repo", "update"], cwd=helmPath)
    p.wait()

    runAndShowCmd("helm dependency update " + helmPath + "/enterprise-logs")

def setupAndInstallGEL():

    output("Installing GEL", True)

    replaceFields = {
        "kubeServiceAccountName" : kubeServiceAccountName,
        "kubeClusterName" : kubeClusterName,
        "gcpBucketName" : gcpBucketName
    }
    createYamlFromTemplate("overrides-template", replaceFields)

    p = subprocess.Popen("helm upgrade --install -f ./enterprise-logs/small.yaml -f " + deployGELFolder + "/overrides.yaml " + helmReleaseName + " ./enterprise-logs --set-file license.contents=" + deployLicenseFolder + "/license-gel.jwt --namespace " + kubeNamespace, cwd=helmPath, shell=True)
    p.wait()

def checkGELInstall():
    output("Checking GEL Install", True)
    stream = os.popen("kubectl get pods --namespace " + kubeNamespace + " | grep gateway | head -1")
    #TODO if pod isn't deployed for some reason, catch error
    firstGatewayPodName = stream.read().split()[0] 

    subprocess.Popen("kubectl port-forward " + firstGatewayPodName + " 3100:3100 --namespace " + kubeNamespace + " & ", shell=True)
    #Wait a few seconds before progressing to ensure the port-forward is setup
    time.sleep(2)

    #Test localhost port forward access to the admin API
    stream = os.popen("curl -s http://localhost:3100/ready")
    isReady = (stream.read() == "ready\n")
    output("Attempting to access admin api (pod:" + firstGatewayPodName + ") on localhost:3100, success[" + str(isReady) + "]")

def checkGELAuthenticatedInstall():
    output("Checking GEL Authenticated Install", True)
    stream = os.popen("curl -s -u :" + tokenGenToken + " http://localhost:3100/admin/api/v1/instances")
    isReady = (stream.read() != "404 page not found\n")
    output("Attempting to access authenticated admin api on localhost:3100, success[" + str(isReady) + "]")

def checkForResourceIP(resourceType, resourceName, ipGrepText):
    stream = os.popen("kubectl describe " + resourceType + " " + resourceName + " --namespace " + kubeNamespace + " | grep '" + ipGrepText + "'")
    cmdOutput = stream.read()
    return cmdOutput

def waitForResource(resourceType, resourceName, ipText, timeoutMax):
    ipOutput = checkForResourceIP(resourceType, resourceName, ipText)

    count = 0
    while (ipOutput == "\n" or ipOutput == ""):
        time.sleep(2)
        ipOutput = checkForResourceIP(resourceType, resourceName, ipText)
        count = count + 1

        if (count > timeoutMax):
            output("Timed out waiting " + str((count - 1) * 2) + " seconds for the resource[" + resourceName + "] to show up in K8s")
            quit()
        else:
            if (count == 1):
                output("Waiting for the resource[" + resourceName + "] to show up but it hasn't yet...")
            sys.stdout.write('\r')
            #TODO use timeoutMax in the output
            sys.stdout.write("[%-45s] %ds (90s timeout)" % ('='*count, 2*count))
            sys.stdout.flush()

    #print("ipOutput " + ipOutput + " -- resourceType: " + resourceType)
    if (ipOutput != ""):
        if (resourceType == "pods"):
            return ipOutput.split()[0]
        else:
            ipOutput = re.findall( r'[0-9]+(?:\.[0-9]+){3}', ipOutput )
            return ipOutput[0]

def deployTokenGenAndInstructionsForToken():

    output("Deploying Token Gen and *retrieving it", True)

    replaceFields = {
        "kubeServiceAccountName" : kubeServiceAccountName
    }
    createYamlFromTemplate("tokengen-template", replaceFields)

    runAndShowCmd("kubectl apply -f " + deployGELFolder + "/tokengen.yaml --force --namespace " + kubeNamespace)
    time.sleep(2)

    podOutput = waitForResource("pods", "ge-logs-tokengen", "Name:", 45)
    if not podOutput.startswith("Error from server"):
        #Extract the token from the logs of the job
        stream = os.popen("kubectl describe job ge-logs-tokengen --namespace " + kubeNamespace + " | grep 'Created pod'")
        cmdOutput = stream.read()
        jobPodName = cmdOutput.split()[6]
        
        runAndShowCmd("kubectl wait --for=condition=complete job/ge-logs-tokengen --namespace " + kubeNamespace)
        
        output("kubectl logs " + jobPodName + " --namespace " + kubeNamespace + " | grep 'Token:'")
        stream = os.popen("kubectl logs " + jobPodName + " --namespace " + kubeNamespace + " | grep 'Token:'")
        cmdOutput = stream.read()
        tokenGenToken = cmdOutput.split()[1]
        output("Your token from the job ge-logs-tokengen: " + tokenGenToken)
    else:
        output("Waited for token but it did not complete, quitting.")

def installGE():

    output("Installing Grafana Enterprise", True)
    runAndShowCmd("kubectl create secret generic ge-license --from-file=" + deployLicenseFolder + "/license-ge.jwt --namespace " + kubeNamespace)

    runAndShowCmd("kubectl create configmap ge-config --from-file=" + deployGELFolder + "/grafana.ini --namespace " + kubeNamespace)

    replaceFields = {
        "kubeServiceAccountName" : kubeServiceAccountName
    }
    createYamlFromTemplate("grafana-enterprise-template", replaceFields)

    p = subprocess.Popen("kubectl apply -f " + deployGELFolder + "/grafana-enterprise.yaml --namespace " + kubeNamespace, shell=True)
    p.wait()

    ipOutput = waitForResource("service", "grafana", "LoadBalancer Ingress", 45)
    
    print("\n") #given stdout has the \r and working on the same line
    output("Go to http://" + ipOutput + ":3000/login")

def installGELIngress():
    
    output("Deploying GEL gateway ingress", True)

    replaceFields = {
        "helmReleaseName" : helmReleaseName,
        "gelGatewayIngress" : gelGatewayIngress
    }
    createYamlFromTemplate("gel-ingress-template", replaceFields)

    p = subprocess.Popen("kubectl apply -f " + deployGELFolder + "/gel-ingress.yaml --namespace " + kubeNamespace, shell=True)
    p.wait()

    ipOutput = waitForResource("ingress", gelGatewayIngress, "IP is now", 45)
    
    print("\n") #given stdout has the \r and working on the same line
    output("Use http://" + ipOutput + ":80/ as the Logs plugin URL setting")

def install():
    timeFunc(checkDependencies)
    timeFunc(createGCPServiceAccount)
    timeFunc(createK8sCluster)
    timeFunc(createK8sServiceAccountsAndConnectToGCP)
    timeFunc(createGCPBucket)
    timeFunc(setupHelm)
    timeFunc(setupAndInstallGEL)
    timeFunc(deployTokenGenAndInstructionsForToken)
    timeFunc(checkGELInstall)
    timeFunc(checkGELAuthenticatedInstall)
    timeFunc(installGELIngress)
    timeFunc(installGE)
    quit()

#Check for command argument "delete'"
if (delete):
    cleanUpInstall()
else:
    install()

#TODO kill localhost:3100 port forward
#sudo lsof -n -i :3100
#kill -9 $pid