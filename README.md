[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](License.md)
![CI](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/actions/workflows/landing-zone-ci.yml/badge.svg)
![Deploy Blockchain Env](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/actions/workflows/deploy-blockchain-env.yml/badge.svg)
![Hardhat CI](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/actions/workflows/hardhat-ci.yml/badge.svg)

---

> **💡 Quick Overview**  
> This repo delivers a complete **Enterprise-Scale Azure Landing Zone** with built-in governance, a hardened **DevTest Lab** sandbox, an **IBFT-consensus Hyperledger Besu network** for integration testing, and **Full CI/CD** for Solidity contracts via GitHub Actions.

---

## 🚀 Quickstart

1. **Clone the repository**
    ```bash
    git clone https://github.com/InfrastructureProductWorks/enterprise-azure-governance.git
    cd enterprise-azure-governance
    ```

2. **Install prerequisites**
   - Azure CLI ≥ 2.40.0 & Bicep CLI
   - Node.js ≥ 16.x & npm

3. **Configure required parameters and secrets**
   - See [Configuration](#-configuration)
   - Set GitHub secrets: `SANDBOX_SUBSCRIPTION_ID`, `DEVTEST_LAB_RG`, etc.

4. **Deploy Landing Zone**
    ```bash
    az login
    az account set --subscription <your-infra-subscription>
    az deployment sub create \
      --location eastus \
      --template-file landing-zone/landing-zone.bicep \
      --parameters @landing-zone/parameters/landing-zone-parameters.json
    ```

5. **Provision DevTest Lab**
    ```bash
    az group create --name rg-sandbox-lab --location eastus
    az lab create \
      --resource-group rg-sandbox-lab \
      --name blockchain-devtestlab \
      --location eastus \
      --storage-type Premium
    ```

6. **Deploy Blockchain Environment and Smart Contracts**
    - Push to main triggers pipelines, or run:
    ```bash
    cd smart-contracts
    npm install
    npx hardhat compile
    npx hardhat test
    export BLOCKCHAIN_RPC="http://rpc-1.blockchain-devtestlab.lab.azure.com:8545"
    npx hardhat run scripts/deploy.js --network devtest
    ```

---

## 📖 Table of Contents

- [About](#-about)
- [Quickstart](#-quickstart)
- [Configuration](#-configuration)
- [Documentation](#-documentation)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Product Vision & Roadmap](#-product-vision--roadmap)
- [CI/CD Pipelines](#-cicd-pipelines)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)
- [License & Support](#-license--support)

---

## 🎯 About

This repository combines:
- **Enterprise-Scale Landing Zone**: Azure Management Groups, Policies, RBAC, networking, monitoring.
- **DevTest Lab Sandbox**: Secure VMs, Just-In-Time (JIT) access, nightly auto-shutdown.
- **IBFT-Based Hyperledger Besu Network**: 4 validator nodes, 2 RPC/API nodes, 2 bootnodes for realistic integration testing.
- **Smart-Contract Framework**: Solidity contracts with OpenZeppelin, NatSpec, Mocha/Chai testing.
- **CI/CD**: GitHub Actions for Bicep deployments and smart-contract pipelines.

---

## ⚙️ Configuration

### Environment Variables & Secrets

- Configure the required values in your local shell or an untracked `.env` file under `smart-contracts/`:
  ```
  PRIVATE_KEY=your_wallet_private_key
  GOERLI_URL=https://...
  MAINNET_URL=https://...
  ETHERSCAN_API_KEY=...
  ```
- [GitHub Secrets](https://docs.github.com/actions/security-guides/encrypted-secrets):
  - `SANDBOX_SUBSCRIPTION_ID`
  - `DEVTEST_LAB_RG`
  - OIDC or PAT for Azure login

### Parameter Files

- Bicep/ARM: see [`landing-zone/parameters/landing-zone-parameters.json`](landing-zone/parameters/landing-zone-parameters.json)
- Document all required parameters; recommend creating your own copy per environment.

---

## 📚 Documentation

- [Repository documentation](docs/architecture.md)
- [DevTest Lab hardening](wiki/devtest-lab-security.md)
- [Monitoring & Diagnostics](wiki/diagnostics-monitoring.md)
- [Smart Contracts CI/CD](wiki/smart-contracts-ci-cd.md)
- [Programmatic deployment](wiki/programmatic-deployment.md)
- [Landing Zone overview](wiki/landing-zone-overview.md)

---

## ✨ Key Features

| Domain             | Technology                       | Highlights                                                                                       |
|--------------------|----------------------------------|--------------------------------------------------------------------------------------------------|
| **Infra**          | Azure Bicep, CLI                 | Management Groups, Policies, NSGs, Hub-Spoke networking                                          |
| **Governance**     | Azure Policy, RBAC               | Enforce VM SKUs, tag compliance, resource locks                                                  |
| **DevTest**        | Azure DevTest Labs, Artifacts    | Secure VM formulas, `install-besu.sh`, JIT, auto-shutdown                                        |
| **Blockchain**     | Hyperledger Besu, IBFT Consensus | 4 validators, 2 RPC/API nodes, 2 bootnodes; custom `genesis.json`                                |
| **SmartContracts** | Hardhat, OpenZeppelin, Mocha     | Local & network tests, coverage reports, NatSpec documentation                                   |
| **CI/CD**          | GitHub Actions                   | Multi-stage workflows: landing-zone, DevTest-lab env, smart-contract pipeline                    |

---

## 🏗 Architecture

![Enterprise Landing Zone Architecture](diagrams/LandingZoneArchitecture.png)

> **Figure:** Enterprise-Scale Landing Zone reference architecture for the Azure governance foundation.

---

## 🛣 Product Vision & Roadmap

**Vision:**  
Enable end-to-end, governed blockchain development on Azure—from infrastructure provisioning to contract deployment—using a repeatable IBFT Besu test network.

### Epics & Goals

| Epic                                      | Goal                                                                                                                       |
|-------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| **Enterprise Foundation**                 | Stand up Azure management groups, policies, subscriptions, and core services to enforce compliance and cost controls.      |
| **DevTest Lab Sandbox**                   | Provision an isolated sandbox subscription with DevTest Lab VMs, artifacts, JIT access, and auto-shutdown.                 |
| **Smart-Contract Framework**              | Build and harden Solidity contracts (access control, governance registry) with OpenZeppelin, tests, and docs.              |
| **CI/CD Automation**                      | Create GitHub Actions pipelines for infrastructure deployment and contract compile/test/deployment.                         |
| **Blockchain Sandbox Infra**              | Deploy/configure an IBFT-consensus Hyperledger Besu network for realistic integration tests.                               |
| **Contract Integration Testing**          | Integrate Hardhat CI against the live Besu network, automating end-to-end smart-contract tests (unit, integration, etc.)   |

---

## 🔄 CI/CD Pipelines

- **landing-zone-ci.yml** — Landing Zone infra deployment
- **deploy-blockchain-env.yml** — IBFT Besu environment deployment
- **hardhat-ci.yml** — Smart-contract compile/test/deploy

CI checks run on pushes and pull requests to `main`. Deployment workflows use
scoped path filters or explicit manual dispatch. Both management deployment
workflows—**Deploy Management Resources** and **Deploy Azure Landing Zone**—are
manual-only and must be started deliberately from GitHub Actions. Status badges
are at the top of this README.

---

## 🛡️ Security

- Hardened network perimeter (NSGs, IP whitelisting)
- Just-In-Time (JIT) VM access
- Diagnostics/logging to Log Analytics
- Secrets managed with Key Vault and GitHub Actions secrets

See [DevTest Lab hardening](wiki/devtest-lab-security.md).

---

## 🧑‍💻 Contributing

Contributions are welcome through pull requests and issues. Open [issues](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/issues) or join [Discussions](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/discussions).

---

## 🛠 Troubleshooting

Use the repository [Discussions](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/discussions) or open an [Issue](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/issues) with the failing workflow, command, and relevant logs.

---

## 📄 License & Support

This project is licensed under the [MIT License](License.md).

For additional assistance, open an [Issue](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/issues) or [Discussion](https://github.com/InfrastructureProductWorks/enterprise-azure-governance/discussions).

---
