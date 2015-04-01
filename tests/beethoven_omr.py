import env
import metaomr
from metaomr import bitimage, deskew

import glob
import numpy as np
import os
import re
import sys
from PIL import Image
import zipfile
from cStringIO import StringIO
import gc

dir_path = sys.argv[1]
imslpid = re.search('IMSLP[0-9]+', dir_path).group(0)
regex = r'\b(' + '|'.join('1 5 6 17 19 20 24 25 27'.split()) + r')\b'
if re.search(regex, dir_path) is None:
    sys.exit(0)
pages = sorted(glob.glob(os.path.join(dir_path, '*.pbm')))
pages = [metaomr.open(page)[0] for page in pages]
for p, page in enumerate(pages):
    sys.stderr.write('%d ' % p)
    try:
        page.preprocess()
        if type(page.staff_dist) is not int:
            raise Exception('staffsize failed')
        deskew.deskew(page)
        page.process()
    except Exception, e:
        print imslpid, p, '-', e
        pages[p] = None

mvmt_start = []
for p, page in enumerate(pages):
    if page is None:
        continue
    ss = page.staves()[:, 0, 0].compressed()
    if len(ss) < 4:
        continue
    if not mvmt_start:
        # Start a new movement on this page
        mvmt_start.append((p, 0))
    else:
        med = np.median(ss)
        starts = ss > med + 50
        for s, sys in enumerate(page.systems):
            if starts[sys['start']:sys['stop']+1].all():
                mvmt_start.append((p, s))
mvmt_start.append((p, len(page.systems)))

output = zipfile.ZipFile(sys.argv[2], 'w', zipfile.ZIP_DEFLATED)

for movement in xrange(len(mvmt_start) - 1):
    mvmt_path = 'mvmt%d' % movement
    for p in xrange(mvmt_start[movement, 0],
                    mvmt_start[movement+1, 0]
                    if mvmt_start[movement+1, 1] == 0
                    else mvmt_start[movement+1, 0] + 1):
        page = pages[p]
        if page is None:
            continue
        img = bitimage.as_hostimage(page.img)[:, :page.orig_size[1]]
        if p == mvmt_start[movement, 0] and mvmt_start[movement, 1] > 0:
            new_system = page.systems[mvmt_start[movement,1]]['start']
            b = page.boundaries[new_system]
            boundary = np.repeat(b[:,1], b[1,0] - b[0,0])
            img = img[:, :min(page.orig_size[1], len(boundary))]
            boundary = boundary[:img.shape[1]]
            img[np.arange(img.shape[0])[:, None] < boundary[None, :]] = 0
        elif (p == mvmt_start[movement+1, 0]
              and 0 < mvmt_start[movement+1, 1] < len(page.systems)):
            new_system = page.systems[mvmt_start[movement+1,1]]['start']
            b = page.boundaries[new_system]
            boundary = np.repeat(b[:,1], b[1,0] - b[0,0])
            img = img[:, :min(page.orig_size[1], len(boundary))]
            boundary = boundary[:img.shape[1]]
            img[np.arange(img.shape[0])[:, None] >= boundary[None, :]] = 0
        img = Image.fromarray(np.where(img, 0, 255).astype(np.uint8))
        buf = StringIO()
        img.save(buf, 'tiff')
        buf.seek(0)
        output.writestr(os.path.join(mvmt_path, 'page%03d.tif' % p), buf.read())
