
class MockImage(object):
    def __init__(self, size, **kwargs):
        self.size = size
        self.kwargs = kwargs
    
    def crop(self, left, top, right, bottom):
        size = min(right-left, self.size[0]), min(bottom-top, self.size[1])
        return MockImage(size, crop=(left, top, right, bottom), source=self)
    
    def resize(self, new_size, resample=None):
        return MockImage(new_size, resize=new_size, source=self)
