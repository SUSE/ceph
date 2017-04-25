// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab

#ifndef CEPH_RBD_MIRROR_TYPES_H
#define CEPH_RBD_MIRROR_TYPES_H

#include <iostream>
#include <memory>
#include <set>
#include <string>
#include <vector>
#include <boost/optional.hpp>

#include "include/rbd/librbd.hpp"
#include "ImageSyncThrottler.h"

namespace rbd {
namespace mirror {

typedef shared_ptr<librados::Rados> RadosRef;
typedef shared_ptr<librados::IoCtx> IoCtxRef;
typedef shared_ptr<librbd::Image> ImageRef;

template <typename I = librbd::ImageCtx>
using ImageSyncThrottlerRef = std::shared_ptr<ImageSyncThrottler<I>>;

struct ImageId {
  std::string global_id;
  std::string id;
  boost::optional<std::string> name;

  explicit ImageId(const std::string &global_id) : global_id(global_id) {
  }
  ImageId(const std::string &global_id, const std::string &id)
    : global_id(global_id), id(id) {
  }
  ImageId(const std::string &global_id, const std::string &id,
          const std::string &name)
    : global_id(global_id), id(id), name(name) {
  }

  inline bool operator==(const ImageId &rhs) const {
    return (global_id == rhs.global_id && id == rhs.id && name == rhs.name);
  }
  inline bool operator<(const ImageId &rhs) const {
    return global_id < rhs.global_id;
  }
};

std::ostream &operator<<(std::ostream &, const ImageId &image_id);

typedef std::set<ImageId> ImageIds;

struct Peer {
  std::string mirror_uuid;
  librados::IoCtx io_ctx;

  Peer() {
  }

  Peer(const std::string &mirror_uuid) : mirror_uuid(mirror_uuid) {
  }

  Peer(const std::string &mirror_uuid, librados::IoCtx &io_ctx)
    : mirror_uuid(mirror_uuid), io_ctx(io_ctx) {
  }

  inline bool operator<(const Peer &rhs) const {
    return mirror_uuid < rhs.mirror_uuid;
  }
  inline bool operator==(const Peer &rhs) const {
    return mirror_uuid == rhs.mirror_uuid;
  }
};

typedef std::set<Peer> Peers;

struct PeerImage : public Peer {
  std::string image_id;

  PeerImage() {
  }
  PeerImage(const std::string &mirror_uuid, const std::string &image_id)
    : Peer(mirror_uuid), image_id(image_id) {
  }
  PeerImage(const std::string &mirror_uuid, librados::IoCtx &io_ctx,
            const std::string &image_id)
    : Peer(mirror_uuid, io_ctx), image_id(image_id) {
  }

  inline bool operator<(const PeerImage &rhs) const {
    if (mirror_uuid != rhs.mirror_uuid) {
      return mirror_uuid < rhs.mirror_uuid;
    } else {
      return image_id < rhs.image_id;
    }
  }
  inline bool operator==(const PeerImage &rhs) const {
    return (mirror_uuid == rhs.mirror_uuid && image_id == rhs.image_id);
  }
};

typedef std::set<PeerImage> PeerImages;

struct peer_t {
  peer_t() = default;
  peer_t(const std::string &uuid, const std::string &cluster_name,
	 const std::string &client_name)
    : uuid(uuid), cluster_name(cluster_name), client_name(client_name)
  {
  }
  peer_t(const librbd::mirror_peer_t &peer) :
    uuid(peer.uuid),
    cluster_name(peer.cluster_name),
    client_name(peer.client_name)
  {
  }
  std::string uuid;
  std::string cluster_name;
  std::string client_name;
  bool operator<(const peer_t &rhs) const {
    return this->uuid < rhs.uuid;
  }
  bool operator()(const peer_t &lhs, const peer_t &rhs) const {
    return lhs.uuid < rhs.uuid;
  }
  bool operator==(const peer_t &rhs) const {
    return uuid == rhs.uuid;
  }
};

std::ostream& operator<<(std::ostream& lhs, const peer_t &peer);

} // namespace mirror
} // namespace rbd


#endif // CEPH_RBD_MIRROR_TYPES_H
