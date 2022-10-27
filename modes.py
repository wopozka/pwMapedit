import tkinter
import tkinter.ttk
import mapCanvas

class mode(object):
    """basic class for all other modes. Just override its methods"""

    def __init__(self, mapCanvas):
        self.mapCanvas = mapCanvas
        self.object_orig_properties = {}
        self.move_coordinates = {'x': None, 'y': None}
        self.objects_to_undecorate = []
        self.objects_to_decorate = []
        self.decorated_objects = []
        self.object_nodes = []
    
    def apply_bindings(self):
        pass
        
    def remove_bindings(self):
        pass
    
    def refresh_decorating_squares(self):
        pass

    def save_orig_properties(self, objectid):
        """
        functions save oryginal properties of the object before selection
        :param objectid:
        :return: {'fill':fill colour}
        """
        print(objectid)
        properties = self.mapCanvas.itemconfig(objectid)
        fillcolour = properties['fill'][-1]
        dash = properties['dash'][-1]
        self.object_orig_properties[objectid] = {'fill': fillcolour, 'dash': dash}
        return

    def apply_orig_properties(self, objectid):
        colour = self.object_orig_properties[objectid]['fill']
        dash = self.object_orig_properties[objectid]['dash']
        print('kolor %s' % colour)
        del(self.object_orig_properties[objectid])
        self.mapCanvas.itemconfig(objectid, fill=colour, dash=dash)

    def decorate_object(self, objectid):
        self.save_object_nodes(objectid)
        self.save_orig_properties(objectid)
        self.mapCanvas.itemconfig(objectid, fill='blue', dash=(5, 5))

    def undecorate_object(self, objectid):
        self.apply_orig_properties(objectid)

    def move_object(self, objectid, delta_x, delta_y):
        self.mapCanvas.move(objectid, delta_x, delta_y)

    def save_object_nodes(self, obj):
        coords = self.mapCanvas.coords(obj)
        pairs = zip(coords[::2], coords[1::2])
        del(self.object_nodes[:])
        for a in list(pairs):
            self.object_nodes.append(a)

    def unregister_mode(self):
        # functions that removes all bindings, and cleans all registers before a new mode i switched on
        # clear all decorated objects
        for a in self.decorated_objects:
            self.undecorate_object(a)
        del(self.objects_to_undecorate[:])
        # clear objects to decorate
        del (self.objects_to_decorate[:])
        self.remove_bindings()


class selectMode(mode):

    def __init__(self, mapCanvas):
        mode.__init__(self, mapCanvas)
        self.apply_bindings()

    def apply_bindings(self):
        self.mapCanvas.bind("<Button-1>", self.mouse_1_pressed)
        self.mapCanvas.bind("<Control-Button-1>", lambda e: self.mouse_1_pressed(e, mod=['control']))
        self.mapCanvas.bind("<ButtonRelease-1>", self.mouse_1_released)
        self.mapCanvas.bind("<B1-Motion>", self.mouse_1_motion)
        
    def remove_bindings(self):
        self.mapCanvas.unbind("<Button-1>")
        self.mapCanvas.unbind("<Control-Button-1>")
        self.mapCanvas.unbind("<ButtonRelease-1>")
        self.mapCanvas.unbind("<B1-Motion>")
        
    def mouse_1_pressed(self, event, mod=None):
        # we have to register the object the mouse pointer is over. For further actions
        a=self.mapCanvas.find_withtag('current')
        print(a)
        if a: # if mouse is over any object
            if self.decorated_objects: # first. There might be at least one object already selected cover it:
                if a in self.decorated_objects: # you clicked on the object that is already decorated
                    pass
                else:
                    if not mod: # in case Ctrl key is not pressed
                        # create list of object to undecorate
                        self.objects_to_undecorate = self.decorated_objects[:]
                        del(self.decorated_objects[:])
                        self.objects_to_decorate.append(a)
                    else:
                        self.objects_to_decorate.append(a)
                        del(self.objects_to_undecorate[:])


            else:
                self.objects_to_undecorate = self.decorated_objects[:]
                self.objects_to_decorate.append(a)

        else: # mouse is not over any object, we have to unselect all and bring old properties of the object

            if not mod:
                self.objects_to_undecorate = self.decorated_objects[:]
                del(self.decorated_objects[:])
            else:
                pass


    def mouse_1_released(self, event):

        # first undecorate decorated objects:
        print('Objects to undecorate %s'%self.objects_to_undecorate)
        for a in self.objects_to_undecorate:
            self.undecorate_object(a)
        del(self.objects_to_undecorate[:])
        # then decorate new objects:
        print(self.objects_to_decorate)
        for a in self.objects_to_decorate:
            self.decorate_object(a)
            self.decorated_objects.append(a)
        del(self.objects_to_decorate[:])
        self.move_coordinates['x'] = None
        self.move_coordinates['y'] = None

    def mouse_1_motion(self, event):
        if not self.move_coordinates['x']:
            self.move_coordinates['x'] = event.x
            self.move_coordinates['y'] = event.y
        delta_x = event.x - self.move_coordinates['x']
        delta_y = event.y - self.move_coordinates['y']
        for obj in self.decorated_objects:
            self. move_object(obj, delta_x, delta_y)

        self.move_coordinates['x'] = event.x
        self.move_coordinates['y'] = event.y

class editNodeMode(mode):
    def __init__(self, mapCanvas):
        mode.__init__(self, mapCanvas)
        self.decorating_squares_ids = []
        self.apply_bindings()
        
    def apply_bindings(self):
        self.mapCanvas.bind("<Button-1>",self.mouse_1_pressed)
        # self.mapCanvas.bind("<Control-Button-1>", lambda e: self.mouse_1_pressed(e, mod=['control']))
        self.mapCanvas.bind("<ButtonRelease-1>",self.mouse_1_released)

    def remove_bindings(self):
        self.mapCanvas.unbind("<Button-1>")
        self.mapCanvas.unbind("<Control-Button-1>")
        self.mapCanvas.unbind("<ButtonRelease-1>")

    def undecorate_object_with_squares(self, obj):
        self.undecorate_object(obj)
        for a in self.decorating_squares_ids:
            self.mapCanvas.delete(a)

    def decorate_object_with_squares(self, obj):
        self.decorate_object(obj)
        decorator_size = 2
        for a in self.object_nodes:
            x1 = a[0] - decorator_size
            y1 = a[1] - decorator_size
            x2 = a[0] + decorator_size
            y2 = a[1] + decorator_size
            self.decorating_squares_ids.append(self.mapCanvas.create_rectangle(x1, y1, x2, y2, fill='black',
                                                                               tags=('decorator',)))

    def refresh_decorating_squares(self):
        print('redraw decorating squares')
        if self.decorated_objects:
            for a in  self.decorating_squares_ids:
                self.mapCanvas.delete(a)
            for a in self.decorated_objects:
                self.save_object_nodes(a)
            self.decorate_object_with_squares(self.decorated_objects[0])


    def mouse_1_pressed(self, event):
         # we have to register the object the mouse pointer is over. For further actions
        a = self.mapCanvas.find_withtag('current')
        print(a)
        if a: # if mouse is over any object
            if self.decorated_objects: # first. There might be at least one object already selected cover it:
                if a in self.decorated_objects: # you clicked on the object that is already decorated
                    pass
                else:
                    self.objects_to_undecorate = self.decorated_objects[:]
                    del(self.decorated_objects[:])
                    self.objects_to_decorate.append(a)

            else:
                self.objects_to_undecorate = self.decorated_objects[:]
                self.objects_to_decorate.append(a)

        else: # mouse is not over any object, we have to unselect all and bring old properties of the object
            self.objects_to_undecorate = self.decorated_objects[:]
            del(self.decorated_objects[:])

    def mouse_1_released(self, event):
        # first undecorate decorated objects:
        print('Objects to undecorate %s'%self.objects_to_undecorate)
        for a in self.objects_to_undecorate:
            self.undecorate_object_with_squares(a)
        del(self.objects_to_undecorate[:])
        # then decorate new objects:
        print(self.objects_to_decorate)
        for a in self.objects_to_decorate:
            self.decorate_object_with_squares(a)
            self.decorated_objects.append(a)
        del(self.objects_to_decorate[:])
        self.move_coordinates['x'] = None
        self.move_coordinates['y'] = None

    def unregister_mode(self):
        mode.unregister_mode(self)
        for a in self.decorating_squares_ids:
            self.mapCanvas.delete(a)