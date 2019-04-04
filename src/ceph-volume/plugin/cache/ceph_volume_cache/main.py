import argparse
import sys
from ceph_volume.api import lvm as api
from ceph_volume.util import disk

"""
The user is responsible for splitting the disk into data and metadata partitions.

If we are to partition a disk to be used as a cache layer, no partition can be
smaller than 2GB because ceph-volume creates vgs with PE = 1GB.

"""


# TODO handle OSD removal
# TODO add a 'cache status' function that shows which OSDs are cached, cache mode, etc
# TODO look into getting cache statistics
# TODO add change caching mode
# TODO  stderr: WARNING: Maximum supported pool metadata size is 16.00 GiB.
# TODO  stderr: WARNING: recovery of pools without pool metadata spare LV is not automated.
# TODO do we want a spare partition or not?

# partition sizes in GB
def _create_cache_lvs(vg_name, md_partition, data_partition, osdid):
    md_partition_size = disk.size_from_human_readable(disk.lsblk(md_partition)['SIZE'])
    data_partition_size = disk.size_from_human_readable(disk.lsblk(data_partition)['SIZE'])

    if md_partition_size < disk.Size(gb=2):
        print('Metadata partition is too small')
        return
    if data_partition_size < disk.Size(gb=2):
        print('Data partition is too small')
        return

    # ceph-volume creates volumes with extent size = 1GB
    # when a new lv is created, one extent needs to be used by LVM itself
    md_lv_size = md_partition_size - disk.Size(gb=1)
    data_lv_size = data_partition_size - disk.Size(gb=1)

    # TODO: update these new LVs' tags (ceph.osd_id, ceph.cluster_fsid, etc.)
    cache_md_lv = api.create_lv(
        'cache_md_osd.' + osdid,
        vg_name,
        size=str(md_lv_size._b) + 'B',
        tags={'ceph.osd_id': osdid, 'ceph.type': 'cache_metadata', 'ceph.partition': md_partition},
        pv=md_partition)

    cache_data_lv = api.create_lv(
        'cache_osd.' + osdid,
        vg_name,
        size=str(data_lv_size._b) + 'B',
        tags={'ceph.osd_id': osdid, 'ceph.type': 'cache_data', 'ceph.partition': data_partition},
        pv=data_partition)

    return cache_md_lv, cache_data_lv


def _create_lvmcache(vg_name, origin_lv, cache_metadata_lv, cache_data_lv):
    # TODO: test that cache data is greater than metadata
    api.create_lvmcache_pool(vg_name, cache_data_lv, cache_metadata_lv)
    api.create_lvmcache(vg_name, cache_data_lv, origin_lv)

    # After this point, cache_metadata_lv and cache_data_lv are hidden, and
    # their names have changed from:
    #   cache_osd.5 to [cache_osd.5_cdata]
    #   cache_md_osd.5 to [cache_osd.5_cmeta]
    # these two partitions keep their tags. A new hidden partition has been created:
    #   [cache_osd.5]
    # We can't set its tags because "Operation not permitted on hidden LV [...]"

    cache_lv = api.get_lv(vg_name=vg_name, lv_name='['+cache_data_lv.name+']')
    if not cache_lv:
        print('Error: can\'t find newly created cache partition.')
        print('Creation of lvmcache probably failed. Aborting.')
        return

    # TODO do we need this tag?
    origin_lv.set_tag('ceph.cache_lv', cache_data_lv.lv_name)
    api.set_lvmcache_caching_mode('writeback', vg_name, origin_lv)

    return cache_lv


def add_lvmcache(vgname, origin_lv, md_partition, cache_data_partition, osdid):
    """
    High-level function to be called. Expects the user or orchestrator to have
    partitioned the disk used for caching.
    """
    # TODO add pvcreate step?
    vg = api.get_vg(vg_name=vgname)
    # TODO don't fail if the LVs are already part of the vg
    api.extend_vg(vg, [md_partition, cache_data_partition])
    cache_md_lv, cache_data_lv = _create_cache_lvs(
        vg.name,
        md_partition,
        cache_data_partition,
        osdid
    )
    cachelv = _create_lvmcache(vg.name, origin_lv, cache_md_lv,
        cache_data_lv)

    return cachelv


def rm_lvmcache(vgname, osd_lv_name):
    osd_lv = api.get_lv(lv_name=osd_lv_name, vg_name=vgname)
    if not osd_lv or not osd_lv.tags['ceph.cache_lv']:
        print('Can\'t find cache data lv')
        return
    vg = api.get_vg(vg_name=vgname)
    cache_lv_name = osd_lv.tags['ceph.cache_lv']

    # get the partitions before removing the LVs
    data_lv_name = '[' + osd_lv.tags['ceph.cache_lv'] + '_cdata]'
    meta_lv_name = '[' + osd_lv.tags['ceph.cache_lv'] + '_cmeta]'
    data_lv = api.get_lv(lv_name=data_lv_name, vg_name=vgname)
    meta_lv = api.get_lv(lv_name=meta_lv_name, vg_name=vgname)
    data_partition = data_lv.tags['ceph.partition']
    md_partition = meta_lv.tags['ceph.partition']

    api.remove_lv(vgname + '/' + cache_lv_name)
    api.reduce_vg(vg, [data_partition, md_partition])

    osd_lv.clear_tag('ceph.cache_lv')


class Cache(object):

    help_menu = 'Deploy Cache'
    _help = """
Deploy lvmcache. Usage:

$> ceph-volume cache add --cachemetadata <metadata partition> --cachedata <data partition> --origin <osd lvm name> --volumegroup <volume group>

or:

$> ceph-volume cache add --cachemetadata <metadata partition> --cachedata <data partition> --osdid <osd id> [--data|--db|--wal]

--data, --db and --wal indicate which partition to cache

Remove cache:

$> ceph-volume cache rm --osdid <id>
    """
    name = 'cache'

    def __init__(self, argv=sys.argv):
        self.mapper = {
        }
        self.argv = argv

    
    def help(self):
        return self._help


    def _get_split_args(self):
        subcommands = self.mapper.keys()
        slice_on_index = len(self.argv) + 1
        pruned_args = self.argv[1:]
        for count, arg in enumerate(pruned_args):
            if arg in subcommands:
                slice_on_index = count
                break
        return pruned_args[:slice_on_index], pruned_args[slice_on_index:]


    def main(self, argv=None):
        main_args, subcommand_args = self._get_split_args()
        parser = argparse.ArgumentParser(
            prog='cache',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.help(),
        )
        parser.add_argument(
            '--cachemetadata',
            help='Cache metadata partition',
        )
        parser.add_argument(
            '--cachedata',
            help='Cache data partition',
        )
        parser.add_argument(
            '--origin',
            help='OSD data partition',
        )
        parser.add_argument(
            '--osdid',
            help='OSD id',
        )
        parser.add_argument(
            '--volumegroup',
            help='Volume group',
        )
        parser.add_argument(
            '--data',
            action='store_true',
            help='cache the OSD\'s data',
        )
        parser.add_argument(
            '--db',
            action='store_true',
            help='cache the OSD\'s db',
        )
        parser.add_argument(
            '--wal',
            action='store_true',
            help='cache the OSD\'s wal',
        )
        args = parser.parse_args(main_args)

        if len(self.argv) <= 1:
            return parser.print_help()

        # TODO make sure OSD is on bluestore
        # TODO make sure OSDs are LVs (deployed with ceph-volume/LVM)

        if args.osdid and args.origin:
            print('Can\'t have --osdid and --origin')
            return

        origin_lv = None
        # This should be under if argv[0] == 'add'
        if args.osdid:
            lvs = api.Volumes()
            for lv in lvs:
                if lv.tags.get('ceph.osd_id', '') == args.osdid:
                    # TODO make sure there is a db or wal partition
                    osdid = args.osdid
                    # TODO update the cache's name accordingly to this
                    # TODO make sure there's a separate wal or db
                    if args.data:
                        origin_lv = api.get_lv(lv_path=lv.tags['ceph.block_device'])
                    elif args.db:
                        # TODO make sure 'ceph.db_device' and others are in tag. ie use tags.get()
                        origin_lv = api.get_lv(lv_path=lv.tags['ceph.db_device'])
                    elif args.wal:
                        origin_lv = api.get_lv(lv_path=lv.tags['ceph.wal_device'])
                    else:
                        origin_lv = api.get_lv(lv_path=lv.tags['ceph.block_device'])
                    break
            if not origin_lv:
                print('Couldn\'t find origin LV for OSD ' + args.osdid)
                return
            vg_name = origin_lv.vg_name
        else:
            # origin is already the LV's name, so no need to look for
            # --data, --db or --wal flags.
            vg_name = args.volumegroup
            origin_lv = api.get_lv(lv_name=args.origin, vg_name=vg_name)
            if not origin_lv:
                print('Couldn\'t find origin LV ' + args.origin)
            osdid = origin_lv.tags.get('ceph.osd_id', None)

        # TODO make sure the OSD exists (ie is on this node)
        if self.argv[0] == 'add':
            add_lvmcache(
                vg_name,
                origin_lv,
                args.cachemetadata,
                args.cachedata,
                osdid)
        elif self.argv[0] == 'rm':
            # TODO verify that the OSD has a cache
            if args.osdid and not args.origin:
                lvs = api.Volumes()
                for lv in lvs:
                    if lv.tags.get('ceph.osd_id', '') == args.osdid and lv.tags.get('ceph.cache_lv', None):
                        origin_lv = lv
                        break
            if not origin_lv:
                print('Couldn\'t find cached LV for OSD ' + args.osdid)
                return
            vg_name = origin_lv.vg_name
            rm_lvmcache(vg_name, origin_lv.name)


if __name__ == '__main__':
    main.Cache()
