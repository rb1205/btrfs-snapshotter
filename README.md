This Script creates and rotates an history of snapshots in a <b>btrfs</b> filesystem that follows an exponential (or custom) concentration over time.


Prerequisites
-------------

* One or more btrfs filesystems
* Python 2.x. No additional python module is needed.
* btrfs-tools in your path


Installation
------------

 # cp snapshotter.py /usr/sbin/


Usage
-----

    snapshotter.py [<operation>] [<options>] <dest_dir>

Example:

    snapshotter.py -c /path/to/subvolume --days=30 --maxqty=50 /path/to/snapshot/directory

The above command will create a snapshot of subvolume at the destination path with the current ISO formatted date as name. By calling it on regular basis (eg: cron.hourly) the script will start deleting snapshot when they're more than 50 starting from the least recent inward following an exponential score system, so that the resulting snapshot will cover all the given timeframe (30 days), but increasing the resolution the closer the date is.

Here's the resulting distribution that the above command would generate after <days> have passed. Use the --sym flag to get this, so you can tune your parameters.

T-0 day (today): 15 snapshots

T-1 day (yesterday): 6 snapshots

T-2 days: 3 snapshots

T-3 days: 2 snapshots

An so on.


Operations
----------
  -c <src>                   : Creates a new snapshot using the provided subvolume as source.
  -C <src>                   : Like -c, but inhibits deletion after creation of the snapshot.
  -s          --sym          : Sym mode. Calculates the outcome and prints the distribution
                                 after <days> have passed. assumes 1 snapshot/hour. it doesn't
                                 need dest_dir to perform the symulation.
  (none)                     : Opposite of -C, deletes any extra snapshot without creating any new.


For any operation other than -C, both --days and --maxqty are required options.


Options
-------
    -d <n>    --days <n>     : REQUIRED. Maximum amounts of days to keep snapshots for. Any
                                 snapshot older than this will be deleted regardless of score
    -n <n>    --maxqty <n>   : REQUIRED. Maximum amount of snapshots to keep. This parameter 
                                 (along with --days and the frequency of snapshots) determines the
                                 concentration of snapshots.
    -r        --readonly     : Creates a read-only snapshot. Relevant only if used with -c or -C.
    -l <str>  --label=<str>  : Defines a label to be used both for creating and filtering snapshots.
    -k <float>               : Parameter used to alter the score formula. Positives values 
                                 concentrates on recent snapshots, negative values even
                                 out the distribution. Defaults to 0.
    -b <...>  --datef=<...>  : Alters the datetime format. Read the FORMAT section in the "date"
                                 manpage. The default datetime format is "%Y.%m.%d_%H.%M"
    -f <frm>  --formula=".." : Used to enter a custom distribution formula that overwrites the
                                 default "x**(1.2**(k-1))"
    -q        --quiet        : Quiet mode. Suppress non-error messages.

