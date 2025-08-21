This repo contains the code for Azure function required for the configuring the Cisco ISE application nodes on the Azure cloud and contains two functions.
- Timer function - It checks the status of the Primary, Secondary and PSN ISE node and if it finds it Up and running then it triggers the second HTTP function to configure the nodes and also checks the node sync status.
- HTTP function - This function is responsible for fetching the Key-values from the azure AppConfig service and excutes the function defined in the main function to configure the ISE Primary, Secondary and PSN nodes.

---

```mermaid
flowchart TD
    subgraph "Azure Functions Host"
        FunctionsHost["Azure Functions Host"]:::host
    end

    subgraph "Serverless Functions"
        TimerTrigger1["TimerTrigger1\n(Timer trigger)"]:::func
        HttpTrigger1["HttpTrigger1\n(HTTP trigger)"]:::func
    end

    subgraph "External Services"
        AzureAppConfig["Azure App Configuration"]:::config
        ISEPrimary["ISE Primary"]:::ise
        ISESecondary["ISE Secondary"]:::ise
        ISEPSN["ISE PSN"]:::ise
    end



    FunctionsHost -->|Schedule Trigger| TimerTrigger1
    TimerTrigger1 -->|Invoke HTTP Function| HttpTrigger1
    TimerTrigger1 -->|Health Check| ISEPrimary
    HttpTrigger1 -->|Get Config| AzureAppConfig
    HttpTrigger1 -->|Configure| ISEPrimary
    HttpTrigger1 -->|Configure| ISESecondary
    HttpTrigger1 -->|Configure| ISEPSN

    click FunctionsHost "https://github.com/rohitti12/ciscoise-terraform-automation-azure-functions/blob/main/host.json"
    click TimerTrigger1 "https://github.com/rohitti12/ciscoise-terraform-automation-azure-functions/blob/main/TimerTrigger1/__init__.py"
    click HttpTrigger1 "https://github.com/rohitti12/ciscoise-terraform-automation-azure-functions/blob/main/HttpTrigger1/__init__.py"
    click Dependencies "https://github.com/rohitti12/ciscoise-terraform-automation-azure-functions/blob/main/requirements.txt"
    click Documentation "https://github.com/rohitti12/ciscoise-terraform-automation-azure-functions/blob/main/README.md"

    classDef host fill:#D0E8FF,stroke:#0366d6,color:#0366d6
    classDef func fill:#D0E8FF,stroke:#1f78b4,color:#1f78b4
    classDef config fill:#C6E0B4,stroke:#238823,color:#238823
    classDef ise fill:#F2F2F2,stroke:#666666,color:#333333
    classDef artifact fill:#FFF2CC,stroke:#b58900,color:#b58900
```
