# Kyverno

A collection of Kyverno policies, educational resources, and implementation patterns designed specifically for financial services environments.

## Overview

This repository contains Kyverno policies and educational materials focused on implementing Kubernetes governance in financial services and regulated environments.

## Contents

- [Discover Kyverno Carousel](./carousel/) - Visual guide explaining Kyverno concepts and financial services use cases
- [Policies](./policies/) - Example Kyverno policies for financial services
- [Implementation Guides](./guides/) - Step-by-step guides for implementing Kyverno

## Getting Started with Kyverno

If you're new to Kyverno, here are the recommended steps to get started:

1. **Explore Kyverno Playground**: Try policies without installation at [playground.kyverno.io](https://playground.kyverno.io/)

2. **Install Kyverno** in your cluster:
   ```bash
   helm repo add kyverno https://kyverno.github.io/kyverno/
   helm repo update
   helm install kyverno kyverno/kyverno

## Official Kyverno Resources

### Documentation
* [Kyverno Official Website](https://kyverno.io/) - Main documentation and overview
* [Kyverno Docs](https://kyverno.io/docs/) - Detailed guides and references
* [Kyverno Policies Library](https://kyverno.io/policies/) - Ready-to-use policy examples

### Code & Repositories
* [Kyverno GitHub Repository](https://github.com/kyverno/kyverno) - Source code and issue tracking
* [Kyverno Helm Charts](https://github.com/kyverno/kyverno/tree/main/charts) - Deployment templates

### Learning & Exploration
* [Kyverno Playground](https://playground.kyverno.io/) - Interactive policy testing environment
* [Kyverno Policy Reporter](https://github.com/kyverno/policy-reporter) - UI for policy violations

### Community
* [Kyverno Slack Channel](https://kubernetes.slack.com/archives/CLGR9BJU9) - Join #kyverno on Kubernetes Slack
* [CNCF Incubation Project Page](https://www.cncf.io/projects/kyverno/) - Project status and information
* [Kyverno Monthly Community Meetings](https://kyverno.io/community/) - Schedule and participation details

### Tutorials & Blog Posts
* [Kyverno Blog](https://kyverno.io/blog/) - Latest features and use cases

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This repository is licensed under Creative Commons Attribution-ShareAlike 4.0 International License.

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

## Acknowledgments
This project builds upon the work of the Kyverno community and the Cloud Native Computing Foundation (CNCF).

Maintained by [Christian Dussol](https://github.com/ChristianDussol), Engineering Manager
