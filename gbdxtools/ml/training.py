import os
import random
import h5py
from collections import defaultdict

class TrainingSet():
    
    def __init__(self, name, ml_type="classification", bbox=[], nclasses=1, _id=None, rm=True):
        self.id = _id
        self.meta = {
            "name": name,
            "bbox": bbox,
            "nclasses": nclasses,
            "ml_type": ml_type
        }
        self.fname = '{}.h5'.format(name)
        if os.path.exists(self.fname) and rm:
            os.unlink(self.fname)
        self.count = defaultdict(int)

        
    def feed(self, data, vtype="train"):
        print 'caching {} {} records'.format(len(data), vtype)
        f = h5py.File(self.fname, 'a')
        try:
            for i in xrange(len(data)):
                if not i % 100:
                    print 'checkpoint', i
                X, Y = data[i]
                self.add_one(X.compute(), Y, i, f=f, vtype=vtype)
        finally:
            f.close()
    
    
    def add_one(self, X, Y, idx, f=None, vtype="train"):
        _close = False
        if f is None:
            _close = True
            f = h5py.File(self.fname, 'a')
        f.create_dataset('{}_X_{}'.format(vtype, idx), data=X)
        f.create_dataset('{}_Y_{}'.format(vtype, idx), data=Y)
        self.count[vtype] += 1
        f.attrs["n_{}".format(vtype)] = self.count[vtype]
        if _close:
            f.close()
    
    
    def generator(self, n=None, vtype="train"):
        f = h5py.File(self.fname, 'r')
        if n is None:
            n = f.attrs["n"]
        try:
            indices = range(n)
            random.shuffle(indices)
            for i in indices:
                X = f["{}_X_{}".format(vtype, i)]
                Y = f["{}_Y_{}".format(vtype, i)]
                yield (X, Y)
        finally:
            f.close()
            
    def save(self):
        # check for an id on the class
        # create a record in VS if not id, else update existing record
        print 'go to an API and think about storage...'
        meta = self.meta
        meta.update({
            "count": dict(self.count),
            "fname": self.fname
        })
        
        return meta
        
    @staticmethod
    def get_batch(name, size, vtype="train"):
        # name/id find the record in the api / fetch the cache / return generateor
        td = Traegnar(name, rm=False)
        return td.generator(n=size, vtype=vtype)
