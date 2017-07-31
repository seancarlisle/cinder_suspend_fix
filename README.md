Cron job to scan for suspended LVM volumes and snapshots. If it finds them, it will use lvchange to resume them, then add them to an email sent out detailing the volumes that have been resumed.
