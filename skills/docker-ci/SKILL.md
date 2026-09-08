---
name: docker-ci
description: Manage Docker build, OCI archive export, registry authentication, multi-platform build, and security scanning actions.
vendor_neutral: true
version: 1.0.0
triggers:
  - "docker build"
  - "docker push"
  - "container scan"
  - "oci tar"
inputs:
  registry:
    type: string
    description: "Container registry URL"
  image_name:
    type: string
    description: "Image repository name"
  tag:
    type: string
    description: "Image tag"
---

# Docker CI Skill

This skill provides guidelines and procedures for AI agents handling Docker container operations within the Forgejo CI Actions repository.

## Capabilities & Patterns

1. **Registry Normalization**:
   - Always strip `http://` or `https://` prefixes and trailing slashes from registry names:
     ```bash
     REGISTRY="${REGISTRY#http://}"
     REGISTRY="${REGISTRY#https://}"
     REGISTRY="${REGISTRY%/}"
     ```

2. **OCI Image Export (`docker-build`)**:
   - Single-platform builds export to local OCI tarball using `docker buildx build --output "type=oci,dest=${OUTPUT}"`.
   - Sanitize output filename: `IMAGE_REF` slashes and colons replaced with underscores (`.oci.tar`).

3. **Multi-Platform Builds (`docker-multi-build`)**:
   - Utilize Docker Buildx with QEMU or native platform builders (`linux/amd64,linux/arm64`).

4. **Container Security Scan (`container-scan` & `security-scan`)**:
   - Integrate Trivy for vulnerability detection and Gitleaks for secrets detection.
   - Respect `severity` thresholds (`HIGH,CRITICAL`) and `ignore_unfixed` flags.

## Standard Action Mapping
- `docker-login`: Registry authentication helper.
- `docker-build`: Build & OCI tarball creation without immediate push.
- `docker-push`: Push OCI or local images to registry.
- `docker-platform-check`: Validate system runner architecture compatibility.
