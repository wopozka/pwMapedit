// Port commands.py: komendy undo/redo.
//
// Inaczej niz w Pythonie komendy nie zmieniaja elementow sceny bezposrednio. Zmieniaja tylko dane obiektu
// w MapData (jedyne zrodlo prawdy), a potem prosza scene o przebudowanie elementu z tych danych
// (MapScene::refresh_object). Obiekty sa wskazywane indeksem w MapData - indeksy sie nie zmieniaja,
// bo usuniecie tylko oznacza obiekt jako usuniety.
#pragma once

#include <QUndoCommand>
#include <optional>
#include <vector>

#include "map_object.hpp"

namespace pwm::gui {

class MapScene;

// Zamiana danych obiektu: stan przed i po zmianie. Wspolna dla przesuwania, odwracania polilinii
// i (w kolejnych etapach) edycji wezlow i wlasciwosci. Odpowiada parze data0_copy/data0 z Pythona.
class ReplaceObjectCmd : public QUndoCommand {
public:
    ReplaceObjectCmd(MapScene* scene, size_t index, MapObject before, MapObject after, const QString& text,
                     QUndoCommand* parent = nullptr);
    void redo() override;
    void undo() override;

private:
    void apply(const MapObject& obj);

    MapScene* scene_;
    size_t index_;
    MapObject before_;
    MapObject after_;
};

// DeleteObjectsCmd: oznacza obiekty jako usuniete (zapis je pomija) i ukrywa ich elementy.
class DeleteObjectsCmd : public QUndoCommand {
public:
    DeleteObjectsCmd(MapScene* scene, std::vector<size_t> indexes, const QString& text,
                     QUndoCommand* parent = nullptr);
    void redo() override;
    void undo() override;

private:
    void set_deleted(bool deleted);

    MapScene* scene_;
    std::vector<size_t> indexes_;
};

// Nowy obiekt (np. druga czesc podzielonej polilinii). Pierwsze redo dodaje obiekt do MapData i tworzy element,
// undo oznacza go jako usuniety, kolejne redo przywraca. Obiekt zostaje w MapData, wiec indeksy sie nie zmieniaja.
class AddObjectCmd : public QUndoCommand {
public:
    AddObjectCmd(MapScene* scene, MapObject obj, const QString& text, QUndoCommand* parent = nullptr);
    void redo() override;
    void undo() override;
    std::optional<size_t> index() const { return index_; }

private:
    MapScene* scene_;
    MapObject obj_;
    std::optional<size_t> index_;
};

}  // namespace pwm::gui
