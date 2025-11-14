# Longhorn Backup Restore

Restores Longhorn volumes from backup. Automatically finds and restores the most recent completed backup for a given volume.

## Features

- 🔍 Automatically finds the latest completed backup for a volume
- 🔄 Restores volume with original configuration from backup metadata
- 📝 Configurable logging levels
- 🐳 Lightweight Docker image based on Python 3.12-slim

## Environment Variables

**LONGHORN_URL** (Required)  
Longhorn API endpoint URL. Default: `http://longhorn-frontend.longhorn-system.svc.cluster.local`

**VOLUME_HANDLE** (Required)  
Longhorn volume name to restore from backup.

**NUMBER_OF_REPLICAS** (Optional)  
Number of replicas for the restored volume. Default: `3`

**LOG_LEVEL** (Optional)  
Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`

## How It Works

1. Fetches all backup volumes from Longhorn
2. Finds the specified volume by name
3. Retrieves all backups for that volume
4. Selects the most recent completed backup
5. Restores the volume using backup metadata (size, block size, backing image, etc.)

## Example Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: authelia-volume-restore
  namespace: authelia
spec:
  template:
    spec:
      containers:
        - name: restore
          image: your-registry/longhorn-backup-restore:latest
          env:
            - name: LONGHORN_URL
              value: http://longhorn-frontend.longhorn-system.svc.cluster.local
            - name: VOLUME_HANDLE
              value: authelia-production-vol
            - name: NUMBER_OF_REPLICAS
              value: "3"
            - name: LOG_LEVEL
              value: INFO
      restartPolicy: Never
  backoffLimit: 3
```

## Building

```bash
docker build -t longhorn-backup-restore:latest .
```

## Local Testing

Enable the port forwarding to access Longhorn API from localhost.
Set the required environment variables and run the script

```bash
export LONGHORN_URL=http://localhost:8000
export VOLUME_HANDLE=my-volume
export NUMBER_OF_REPLICAS=2
export LOG_LEVEL=DEBUG
python3 backup-restore.py
```

## Requirements

- Python 3.12+
- `requests` library (see `requirements.txt`)
- Access to Longhorn API endpoint

## Notes

- The script restores only the Longhorn volume, not Kubernetes PV/PVC objects
- To create PV/PVC, you need to handle that separately (e.g., using Helm charts or Kubernetes manifests)
- The most recent completed backup is automatically selected
- Volume configuration (size, block size, backing image) is read from backup metadata
- For a more complete version which also creates PV/PVC objects, see the [original repository](https://github.com/wahooli/longhorn-backup-restore)
