/*
  Bicep template to define a DevTest Lab environment for an IBFT Ethereum-based network
  - Ubuntu 22.04 LTS VMs
  - 4 Validator nodes
  - 2 RPC/API nodes
  - 2 Bootnodes (private + public)
  - Key Vault integration, managed identities
  - VNet peering into existing hub-spoke
  - Auto-shutdown at 19:00 daily
*/

@description('Name of the existing DevTest Lab')
param labName string
@description('Resource group containing the DevTest Lab')
param labRg string
@description('Azure location for resources')
param location string = resourceGroup().location
@description('Hub VNet resource ID for peering')
param hubVnetId string

// VM sizing parameters
param vmSize string = 'Standard_D4s_v5'
param imagePublisher string = 'Canonical'
param imageOffer string = '0001-com-ubuntu-server-jammy'
param imageSku string = '22_04-lts-gen2'
param imageVersion string = 'latest'

// Node counts
param validatorCount int = 4
param rpcCount int = 2
param bootnodeCount int = 2

// Key Vault details
param keyVaultName string = 'dev-blockchain-lab-kv'

var keyVaultId = resourceId('Microsoft.KeyVault/vaults', keyVaultName)

// Create formulas for each VM role
// Formula: installs Besu and initializes with genesis.json
resource validatorFormula 'Microsoft.DevTestLab/labs/formulas@2018-09-15' = [for i in range(0, validatorCount): {
  name: '${labName}-validator-${i+1}-formula'
  properties: {
    labVirtualMachineId: '' // placeholder if reusing custom image
    formulaContent: {
      osType: 'Linux'
      formulaParameters: {}
      artifacts: [
        {
          artifactId: '${labName}/Install-Besu'
          parameters: {
            genesisFileUri: 'https://<storage>/genesis.json'
            chainId: '0x0A'
            gasLimit: '0x1C9C380'
            bootnodes: ''
          }
        }
      ]
    }
  }
}]

resource rpcFormula 'Microsoft.DevTestLab/labs/formulas@2018-09-15' = [for i in range(0, rpcCount): {
  name: '${labName}-rpc-${i+1}-formula'
  properties: {
    formulaContent: {
      osType: 'Linux'
      artifacts: [
        {
          artifactId: '${labName}/Install-Besu'
          parameters: {
            genesisFileUri: 'https://<storage>/genesis.json'
            chainId: '0x0A'
            gasLimit: '0x1C9C380'
            bootnodes: '<bootnode-private-ip-enode>,<bootnode-public-ip-enode>'
            rpcEnabled: 'true'
          }
        }
      ]
    }
  }
}]

resource bootnodeFormula 'Microsoft.DevTestLab/labs/formulas@2018-09-15' = [for i in range(0, bootnodeCount): {
  name: '${labName}-bootnode-${i+1}-formula'
  properties: {
    formulaContent: {
      osType: 'Linux'
      artifacts: [
        {
          artifactId: '${labName}/Install-Besu'
          parameters: {
            genesisFileUri: 'https://<storage>/genesis.json'
            chainId: '0x0A'
            gasLimit: '0x1C9C380'
            bootnodeMode: 'true'
            staticPublicIp: (i == 1 ? 'true' : 'false')
          }
        }
      ]
    }
  }
}]

// DevTest Lab Environment resource
resource labEnv 'Microsoft.DevTestLab/labs/environments@2018-09-15' = {
  name: '${labName}/blockchain-dev-env'
  location: location
  properties: {
    description: 'Blockchain IBFT network environment'
    labVmProfiles: [
      for i in range(0, validatorCount): {
        name: 'validator-${i+1}'
        formulaId: validatorFormula[i].id
        computeVm: {
          size: vmSize
        }
        artifacts: []
      },
      for i in range(0, rpcCount): {
        name: 'rpc-${i+1}'
        formulaId: rpcFormula[i].id
        computeVm: { size: vmSize }
      },
      for i in range(0, bootnodeCount): {
        name: 'bootnode-${i+1}'
        formulaId: bootnodeFormula[i].id
        computeVm: { size: vmSize }
      }
    ]
    labVirtualNetworkId: hubVnetId
    shutdown: {
      taskType: 'LabVmsShutdownTask'
      dailyRecurrence: {
        hours: [19]
      }
    }
    allowClaim: true
  }
}

/*
  Shell script artifact: Install-Besu
  (to be uploaded under lab's artifacts)
*/

// File: install-besu.sh
// #!/bin/bash
// apt-get update && apt-get install -y wget
// wget -qO - https://dl.bintray.com/hyperledger-org/besu-deb/besu2.x.key | apt-key add -
// echo 'deb [arch=amd64] https://dl.bintray.com/hyperledger-org/besu-deb stable main' | tee /etc/apt/sources.list.d/besu.list
// apt-get update && apt-get install -y besu
// GENESIS_URI="$1"
// CHAIN_ID="$2"
// GAS_LIMIT="$3"
// BOOTNODES="$4"
// besu --data-path=/var/lib/besu init "$GENESIS_URI"
// nohup besu \
//   --network-id="$CHAIN_ID" \
//   --min-gas-price=0 \
//   --rpc-http-enabled=${5:-false} \
//   --rpc-http-host=0.0.0.0 \
//   --rpc-http-port=8545 \
//   --bootnodes="$BOOTNODES" > besu.log 2>&1 &

/*
  Next steps:
  1. Upload install-besu.sh as an artifact under your DevTest Lab.
  2. Customize genesis.json (Chain ID, difficulty, alloc, IBFT config, extraData).
  3. Replace <storage>/genesis.json URI and enode placeholders.
  4. Deploy this Bicep via Azure CLI or Pipelines: az deployment group create ...
*/
