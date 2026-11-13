#include "commands.hpp"

#include "map_items.hpp"
#include "map_scene.hpp"

namespace pwm::gui {

ReplaceObjectCmd::ReplaceObjectCmd(MapScene* scene, size_t index, MapObject before, MapObject after,
                                   const QString& text, QUndoCommand* parent)
    : QUndoCommand(text, parent), scene_(scene), index_(index), before_(std::move(before)), after_(std::move(after)) {}

void ReplaceObjectCmd::redo() { apply(after_); }

void ReplaceObjectCmd::undo() { apply(before_); }

void ReplaceObjectCmd::apply(const MapObject& obj) {
    MapData* map = scene_->map();
    if (!map || index_ >= map->objects().size()) return;
    map->objects()[index_] = obj;
    scene_->refresh_object(index_);
}

DeleteObjectsCmd::DeleteObjectsCmd(MapScene* scene, std::vector<size_t> indexes, const QString& text)
    : QUndoCommand(text), scene_(scene), indexes_(std::move(indexes)) {}

void DeleteObjectsCmd::redo() { set_deleted(true); }

void DeleteObjectsCmd::undo() { set_deleted(false); }

void DeleteObjectsCmd::set_deleted(bool deleted) {
    MapData* map = scene_->map();
    if (!map) return;
    for (size_t index : indexes_) {
        map->set_map_object_deleted(index, deleted);
        if (MapObjectItem* item = scene_->item_for_object(index)) {
            if (deleted) item->graphics_item()->setSelected(false);
            item->refresh();
        }
    }
}

}  // namespace pwm::gui
