#!/usr/bin/python3
import os
import json
import logging
import requests
from requests.exceptions import RequestException


def get_backup_volumes(longhorn_url):
    """Fetch all backup volumes from Longhorn API"""
    url = f"{longhorn_url}/v1/backupvolumes"
    logging.debug("Fetching backup volumes from: %s", url)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logging.debug("Backup volumes response: %s", response.text)
        return response.json()
    except RequestException as e:
        logging.error("Failed to fetch backup volumes: %s", e)
        raise


def find_backup_volume_by_name(backup_volumes_data, volume_name):
    """Find a specific backup volume by volumeName"""
    if 'data' not in backup_volumes_data:
        logging.warning("No 'data' field in response")
        return None

    for backup_volume in backup_volumes_data['data']:
        if backup_volume.get('volumeName') == volume_name:
            return backup_volume

    return None


def get_backup_list(longhorn_url, backup_volume_id):
    """Fetch list of backups for a specific backup volume"""
    url = f"{longhorn_url}/v1/backupvolumes/{backup_volume_id}?action=backupList"
    logging.debug("Fetching backup list from: %s", url)

    try:
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        logging.debug("Backup list response: %s", response.text)
        return response.json()
    except RequestException as e:
        logging.error("Failed to fetch backup list: %s", e)
        raise


def find_latest_backup(backup_list_data):
    """Find the latest completed backup from the list"""
    if 'data' not in backup_list_data or not backup_list_data['data']:
        return None

    # Filter for completed backups
    completed_backups = [
        b for b in backup_list_data['data']
        if b.get('state') == 'Completed'
    ]

    if not completed_backups:
        return None

    # Sort by created timestamp and get the latest
    completed_backups.sort(key=lambda x: x.get('created', ''), reverse=True)
    return completed_backups[0]


def restore_volume_from_backup(longhorn_url, backup_volume, backup_details,
                               number_of_replicas=3):
    """Restore a volume from backup"""
    url = f"{longhorn_url}/v1/volumes"

    volume_name = backup_volume.get('volumeName')
    backup_target_name = backup_volume.get('backupTargetName', 'default')

    # Extract values from backup details
    from_backup_url = backup_details.get('url')
    volume_size = backup_details.get('volumeSize')
    block_size = backup_details.get('blockSize')

    # Extract labels to preserve Kubernetes metadata
    labels = backup_details.get('labels', {})

    # Prepare the restore payload with values from backup
    payload = {  # TODO: some fields are hardcoded, make them configurable if needed
        "name": volume_name,
        "numberOfReplicas": number_of_replicas,
        "dataEngine": "v1",
        "backingImage": backup_details.get('volumeBackingImageName', ''),
        "encrypted": False,
        "restoreVolumeRecurringJob": "ignored",
        "nodeSelector": [],
        "diskSelector": [],
        "backupBlockSize": block_size,
        "fromBackup": from_backup_url,
        "backupTargetName": backup_target_name,
        "volumeName": volume_name,
        "staleReplicaTimeout": 20,
        "size": volume_size
    }

    logging.info("Restoring volume '%s' from backup", volume_name)
    logging.debug("Restore payload: %s", json.dumps(payload, indent=2))

    try:
        response = requests.post(url, json=payload, timeout=30)
        logging.debug("Restore response: %s", response.text)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error("Failed to restore volume: %s", e)
        if hasattr(e.response, 'text'):
            logging.error("Response: %s", e.response.text)
        raise


def main():
    # Setup logging
    level_name = os.getenv('LOG_LEVEL', 'INFO')
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level)

    # Get environment variables
    longhornUrl = os.getenv('LONGHORN_URL')
    volumeHandle = os.getenv('VOLUME_HANDLE')
    numberOfReplicas = int(os.getenv('NUMBER_OF_REPLICAS', '2'))

    logging.info("LONGHORN_URL=%s", longhornUrl)
    logging.info("VOLUME_HANDLE=%s", volumeHandle)
    logging.info("NUMBER_OF_REPLICAS=%d", numberOfReplicas)

    # Check if longhornUrl and volumeHandle are set
    if not longhornUrl:
        logging.error("LONGHORN_URL environment variable is not set")
        raise ValueError("LONGHORN_URL environment variable is not set")
    if not volumeHandle:
        logging.error("VOLUME_HANDLE environment variable is not set")
        raise ValueError("VOLUME_HANDLE environment variable is not set")

    # Fetch all backup volumes
    logging.info("Fetching backup volumes...")
    backup_volumes = get_backup_volumes(longhornUrl)

    total_volumes = len(backup_volumes.get('data', []))
    logging.info("Found %d backup volume(s)", total_volumes)

    # Find the specific backup volume
    backup_volume = find_backup_volume_by_name(backup_volumes, volumeHandle)

    if not backup_volume:
        logging.error("Backup volume with name '%s' not found", volumeHandle)
        raise ValueError(f"Backup volume '{volumeHandle}' not found")

    # Log backup volume details
    logging.debug("Found backup volume: %s",
                  json.dumps(backup_volume, indent=2))

    backup_volume_id = backup_volume.get('id')
    logging.info("Backup volume ID: %s", backup_volume_id)

    # Fetch backup list for this volume
    logging.info("Fetching backup list for volume '%s'...", volumeHandle)
    backup_list = get_backup_list(longhornUrl, backup_volume_id)

    total_backups = len(backup_list.get('data', []))
    logging.info("Found %d backup(s) for volume", total_backups)

    # Find the latest backup
    latest_backup = find_latest_backup(backup_list)

    if not latest_backup:
        logging.error(
            "No completed backup found for volume '%s'", volumeHandle)
        raise ValueError(
            f"No completed backup found for volume '{volumeHandle}'")

    logging.info("Latest backup: %s (created: %s, state: %s)",
                 latest_backup.get('name'),
                 latest_backup.get('created'),
                 latest_backup.get('state'))
    logging.debug("Backup details: %s", json.dumps(latest_backup, indent=2))

    # Restore the volume
    restored_volume = restore_volume_from_backup(
        longhornUrl,
        backup_volume,
        latest_backup,
        numberOfReplicas
    )

    logging.info("Volume restore initiated successfully")
    logging.debug("Restored volume details: %s",
                  json.dumps(restored_volume, indent=2))

    return restored_volume


if __name__ == "__main__":
    try:
        result = main()
        logging.info("Volume restored successfully")
    except Exception as e:
        logging.error("An error occurred: %s", e)
        exit(1)
