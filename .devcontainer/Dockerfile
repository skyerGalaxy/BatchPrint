FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

# System deps for Rust/Tauri build and general dev tools
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		ca-certificates \
		curl \
		pkg-config \
		libssl-dev \
		libgtk-3-dev \
		libwebkit2gtk-4.1-dev \
		libsoup-3.0-dev \
		libjavascriptcoregtk-4.1-dev \
		libayatana-appindicator3-dev \
		librsvg2-dev \
		patchelf \
		python3-venv \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/BatchPrint
