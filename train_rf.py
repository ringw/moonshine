import numpy as np
from sklearn.ensemble import RandomForestClassifier
import moonshine
from moonshine import staffsize, rotate
import scipy.misc
import scipy.ndimage
import glob
import os.path
import cPickle

COLOR_LABELS = {
    (255, 0, 0): "empty_note",
    (0, 0, 255): "filled_note",
    (1, 0, 0): "treble_clef",
    (2, 0, 0): "small_treble_clef",
    (3, 0, 0): "bass_clef",
    (4, 0, 0): "small_bass_clef",
    (255, 255, 0): "flat",
    (255, 0, 255): "natural",
    (0, 255, 255): "sharp"
}
PATCH_SIZE = 17
LABEL_SIZE = 3

labeled_data = glob.glob('labels/*.png')
patches = np.zeros((0, PATCH_SIZE * PATCH_SIZE), np.bool)
patch_labels = []
for labels in labeled_data:
    label_img = scipy.misc.imread(labels)
    image_path = os.path.join('samples', os.path.basename(labels))
    image, = moonshine.open(image_path)
    staffsize.staffsize(image)
    assert image.staff_dist >= 8
    image_scale = 8.0 / image.staff_dist
    image = scipy.misc.imresize(image.byteimg[:image.orig_size[0],
                                              :image.orig_size[1]].astype(bool),
                                image_scale,
                                interp='nearest')
    num_label_patches = 0
    for label_type, label_name in COLOR_LABELS.iteritems():
        our_patches = []
        is_label = label_img[:, :, :3] == np.array([[label_type]])
        # When scaling down, need to ensure each label pixel maps to some
        # new pixel and isn't overwritten by the background
        label_y, label_x = np.where(is_label.all(axis=-1))
        if len(label_y):
            label_y = (label_y * image_scale).astype(int)
            label_x = (label_x * image_scale).astype(int)
            scale_label = np.zeros_like(image)
            scale_label[label_y, label_x] = 1
            scale_label = scipy.ndimage.binary_dilation(scale_label,
                                    iterations=LABEL_SIZE / 2)
            scale_label[:PATCH_SIZE / 2, :] = 0
            scale_label[-PATCH_SIZE / 2 - 1:, :] = 0
            scale_label[:, :PATCH_SIZE / 2] = 0
            scale_label[:, -PATCH_SIZE / 2 - 1:] = 0
            for y, x in np.c_[np.where(scale_label)]:
                patch = image[y - PATCH_SIZE / 2 : y + PATCH_SIZE / 2 + 1,
                              x - PATCH_SIZE / 2 : x + PATCH_SIZE / 2 + 1]
                our_patches.append(patch.ravel())
            patches = np.concatenate([patches, our_patches])
            patch_labels += [label_name for i in our_patches]
            num_label_patches += len(our_patches)

    # Find equal number of background patches
    bg_patches = []
    while len(bg_patches) < num_label_patches:
        x = np.random.randint(PATCH_SIZE / 2,
                              image.shape[1] - PATCH_SIZE / 2)
        y = np.random.randint(PATCH_SIZE / 2,
                              image.shape[0] - PATCH_SIZE / 2)
        patch = image[y - PATCH_SIZE / 2 : y + PATCH_SIZE / 2 + 1,
                      x - PATCH_SIZE / 2 : x + PATCH_SIZE / 2 + 1]
        if patch.any():
            bg_patches.append(patch.ravel())
    patches = np.concatenate([patches, bg_patches])
    patch_labels += ["background" for patch in bg_patches]

rf = RandomForestClassifier(n_estimators=8)
rf.fit(patches, patch_labels)
cPickle.dump(rf, open('classifier.pkl', 'wb'))
