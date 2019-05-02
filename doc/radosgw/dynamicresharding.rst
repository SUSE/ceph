.. _rgw_dynamic_bucket_index_resharding:

===================================
RGW Dynamic Bucket Index Resharding
===================================

.. versionadded:: Luminous

A large bucket index can lead to performance problems. In order
to address this problem we introduced bucket index sharding.
Until Luminous, changing the number of bucket shards (resharding)
needed to be done offline. Starting with Luminous we support
online bucket resharding.

Each bucket index shard can handle its entries efficiently up until
reaching a certain threshold number of entries. If this threshold is exceeded the system
can encounter performance issues.
The dynamic resharding feature detects this situation and automatically
increases the number of shards used by the bucket index,
resulting in the reduction of the number of entries in each bucket index shard.
This process is transparent to the user.

The detection process runs:

1. when new objects are added to the bucket and
2. in a background process that periodically scans all the buckets.

The background process is needed in order to deal with existing buckets in the system that are not being updated.
A bucket that requires resharding is added to the resharding queue and will be
scheduled to be resharded later.
The reshard threads run in the background and execute the scheduled resharding tasks, one at a time.

Multisite
=========

Dynamic resharding is not supported in a multisite environment.


Configuration
=============

Enable/Disable dynamic bucket index resharding:

- ``rgw_dynamic_resharding``:  true/false, default: true

Configuration options that control the resharding process:

- ``rgw_reshard_num_logs``: number of shards for the resharding queue, default: 16

- ``rgw_reshard_bucket_lock_duration``: duration, in seconds, of lock on bucket obj during resharding, default: 120 seconds

- ``rgw_max_objs_per_shard``: maximum number of objects per bucket index shard before resharding is triggered, default: 100000 objects

- ``rgw_reshard_thread_interval``: maximum time, in seconds, between rounds of resharding queue processing, default: 600 seconds


Admin commands
==============

Add a bucket to the resharding queue
------------------------------------

::

   # radosgw-admin reshard add --bucket <bucket_name> --num-shards <new number of shards>

List resharding queue
---------------------

::

   # radosgw-admin reshard list

Process tasks on the resharding queue
-------------------------------------

::

   # radosgw-admin reshard process

Bucket resharding status
------------------------

::

   # radosgw-admin reshard status --bucket <bucket_name>

Cancel pending bucket resharding
--------------------------------

Note: Ongoing bucket resharding operations cannot be cancelled. ::

   # radosgw-admin reshard cancel --bucket <bucket_name>

Manual immediate bucket resharding
----------------------------------

::

   # radosgw-admin bucket reshard --bucket <bucket_name> --num-shards <new number of shards>


Troubleshooting
===============

Clusters prior to Luminous 12.2.11 and Mimic 13.2.5 left behind stale bucket
instance entries, which were not automatically cleaned up. The issue also affected
LifeCycle policies, which were not applied to resharded buckets anymore. Both of
these issues can be worked around using a couple of radosgw-admin commands.

Stale instance management
-------------------------

List the stale instances in a cluster that are ready to be cleaned up.

::

   # radosgw-admin reshard stale-instances list

Clean up the stale instances in a cluster. Note: cleanup of these
instances should only be done on a single site cluster.

::

   # radosgw-admin reshard stale-instances rm


Lifecycle fixes
---------------

For clusters that had resharded instances, it is highly likely that the old
lifecycle processes would have flagged and deleted lifecycle processing as the
bucket instance changed during a reshard. While this is fixed for newer clusters
(from Mimic 13.2.6 and Luminous 12.2.12), older buckets that had lifecycle policies and
that have undergone resharding will have to be manually fixed.

The command to do so is:

::

   # radosgw-admin lc reshard fix --bucket {bucketname}


As a convenience wrapper, if the ``--bucket`` argument is dropped then this
command will try and fix lifecycle policies for all the buckets in the cluster.

Object Expirer fixes
--------------------

Similar to the Lifecycle fixes, swift object expiry on resharded buckets on
older clusters that had an expiry time before the cluster was upgraded with
fixes will have dropped entries off the log pool and no longer deleted the
object. While object expiry for dates in the future will be handled correctly by
an upgraded RGW, for objects where delete_at times are in the past and still
present in the cluster can be found out and deleted with the following commands.

Listing:

::

   # radosgw-admin objects expire-stale list --bucket {bucketname}

This will return a json of object names and their delete at times.

Deleting:

::

   # radosgw-admin objects expire-stale rm --bucket {bucketname}


This will return a json with object names, delete at times and status of deletion.
