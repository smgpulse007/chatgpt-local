#!/usr/bin/env pwsh
param(
    [switch]$Detach
)

$composeFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "../docker/compose.yml"
if ($Detach) {
    docker compose -f $composeFile up --build -d
} else {
    docker compose -f $composeFile up --build
}
