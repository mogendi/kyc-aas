from .models import ( Usr, FileInstances, NatId, KRAPinCert, Validator )
import pathlib, pytesseract, pdf2image, PIL, io, numpy, re, binascii, cv2, requests
from django.core.files.storage import FileSystemStorage

cache = {}

'''
Check file Type
'''
def file_type(ext):
    types = {"image": ['.jpg', '.gif', '.jpeg', '.png', '.tiff', '.bmp'],
                "video": ['.webm', '.mpeg4', '.3gpp', '.mov', '.avi', '.mpegps', '.wmv', '.flv'],
                "document": ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.pdf'],
                "code": ['.c', '.cpp', '.py', '.java', '.html', '.css']}
    for key in types:
        if ext in types[key]:
            return key
'''
Creates new file instance/ uploads it
'''
def new_file(c, r, fn=None):

    if fn is not None:
        fa = r.FILES.get(fn)
        if fa is None:
            return fa
        up = c.chest_dir + '/' + fa.name
        fs = FileSystemStorage(location=c.chest_dir)
        fs.save(fa.name, fa)
        ft = pathlib.Path(fa.name).suffix
        fi = FileInstances.objects.create(chest=c, upload_path=up, file_type=file_type(ft))
        fi.save()
        return fi
    else:
        fis = []
        for ft in r.FILES:
            fa = r.FILES.get(ft)
            up = c.chest_dir + '/' + fa.name
            fs = FileSystemStorage(location=c.chest_dir)
            fs.save(fa.name, fa)
            ft = pathlib.Path(fa.name).suffix
            fi = FileInstances.objects.create(chest=c, upload_path=up, file_type=file_type(ft))
            fi.save()
            fis.append(fi)
        return fis

'''
get image data depending on the file type
'''
def file_contents(f):
    f.seek(0)
    fc = f.read()
    ft = file_type(pathlib.Path(f.name).suffix)
    imgs = []
    if ft == "document":
        pages = pdf2image.convert_from_bytes(fc)
        for pg in pages:
            dt  = numpy.array(pg)
            imgs.append(dt)
    if ft == "image":
        img = PIL.Image.open(io.BytesIO(fc))
        img = img.convert('RGB')
        img = numpy.array(img)
        imgs.append(img)
    return imgs

'''
Extract an RE pattern from image if it can
'''
def image_extractor(ptn, fa):
    fa.seek(0)
    fc = fa.read()

    hsh = hex(binascii.crc32(fc))

    cached = None

    if cached is None:
        ft = file_type(pathlib.Path(fa.name).suffix)
        if ft == "document":
            pages = pdf2image.convert_from_bytes(fc)
            dct = ""
            for pg in pages:
                pg = pg.convert('RGBA')
                data = numpy.array(pg)
                red, green, blue, alpha = data.T
                black_to_gray = (red > 140) & (blue > 130) & (green > 128)
                data[..., :-1][black_to_gray.T] = (255, 255, 255) 
                pg = PIL.Image.fromarray(data)
                txt = pytesseract.image_to_string(pg)
                dct = dct + txt + "\n"
            idn = re.search(ptn, dct)
            cache[hsh] = dct
            if idn:
                return idn.group()
            else:
                return False
        elif ft == "image":
            img = PIL.Image.open(io.BytesIO(fc))
            img = img.convert('RGBA')
            data = numpy.array(img)
            red, green, blue, alpha = data.T
            black_to_gray = (red > 140) & (blue > 130) & (green > 128)
            data[..., :-1][black_to_gray.T] = (255, 255, 255) 
            img = PIL.Image.fromarray(data)
            txt = pytesseract.image_to_string(img)
            idn = re.search(ptn, txt)
            print(idn)
            cache[hsh] = txt
            print(txt)
            if idn:
                return idn.group()
            else:
                return False
        else:
            # assume its an image
            img = PIL.Image.open(io.BytesIO(fc))
            img = img.convert('RGBA')
            data = numpy.array(img)
            red, green, blue, alpha = data.T
            black_to_gray = (red > 140) & (blue > 130) & (green > 128)
            data[..., :-1][black_to_gray.T] = (255, 255, 255) 
            img = PIL.Image.fromarray(data)
            txt = pytesseract.image_to_string(img)
            idn = re.search(ptn, txt)
            cache[hsh] = txt
            if idn:
                return idn.group()
            else:
                return False

    else:
        idn = re.search(ptn, cached)
        if idn:
            return idn.group()
        else:
            return False

'''
unpack ID into relevant model
'''
def unpack_id(r, fl):
    usr = Usr.objects.get(def_usr = r.user)

    fa = r.FILES.get("userid")
    idn = image_extractor(r'[0-9]{8}', fa)
    uname = image_extractor(r"(FULL NAMES)[ |\n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    bday = image_extractor(r'(DATE OF BIRTH)[ |\n]*[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', fa)
    bday = re.search(r'[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', bday).group()

    # these fields aren't sure to be there (not checked by the 'check_id' view)
    sex = image_extractor(r'(SEX)[ |\n]*(MALE)|(FEMALE)', fa)
    if sex is not False:
        sex = sex[3:]

    dob = image_extractor(r'(DISTRICT OF BIRTH)[ |\n]*[A-Z ]*', fa)
    if dob is not False:
        dob = dob[17:]

    poi = image_extractor(r'(PLACE OF ISSUE)[ |\n]*[A-Z ]*', fa)
    if poi is not False:
        poi = poi[15:]

    doi = image_extractor(r'(DATE OF ISSUE)[ |\n]*[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', fa)
    if doi is not False:
        doi = re.search(r'[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', doi).group()

    NatId.objects.create(
        id_number = idn, 
        full_name = uname,
        bdate = bday,
        sex = sex,
        district_ob = dob,
        place_oi = poi,
        issue_date = doi,

        usr = usr,
        file=fl.id
    )

'''
unpack kra pin cert into relevant model
'''
def unpack_kra(r, fl):
    usr = Usr.objects.get(def_usr = r.user)

    fa = r.FILES.get("userkra")
    idn = image_extractor(r'[A-G][0-9]{9}[A-G]', fa)
    uname = image_extractor(r"(Taxpayer Name)[ \n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    
    email = image_extractor(r"(Email Address)[ \n]*([A-Z'’.@ ]+)", fa)
    email = email[13:]

    bld = image_extractor(r"(Building :)[ \n]*([A-Za-z0-9 ]+)", fa)
    if bld is not False:
        bld = bld[10:]

    rd = image_extractor(r"(Street/Road :)[ \n]*([A-Za-z ]+)", fa)
    if rd is not False:
        rd = rd[13:]

    ct = image_extractor(r"(City/Town :)[ \n]*([A-Za-z ]+)", fa)
    if ct is not False:
        ct = ct[11:]

    cn = image_extractor(r"(County :)[ \n]*([A-Za-z ]+)", fa)
    if cn is not False:
        cn = cn[8:]

    pbx = image_extractor(r"(P.O. Box :)[ \n]*[0-9]+", fa)
    if pbx is not False:
        pbx = pbx[11:]

    cd = image_extractor(r"(Postal Code:)[ \n]*[0-9]+", fa)
    if cd is not False:
        cd = cd[13:]

    KRAPinCert.objects.create(
        pin = idn,
        taxpayer_name = uname,
        email = email,
        addr = "{0} {1}, {2}, {3}".format(bld, rd, ct, cn),
        po_box = "{0}-{1}".format(pbx, cd),

        usr = usr,
        file=fl.id
    )

def face_detect(frame):
    cascPath = "kycweb/haarcascade_frontalface_default.xml"
    faceCascade = cv2.CascadeClassifier(cascPath)

    nparr = numpy.fromstring(frame.read(), numpy.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    frame = img_np

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    return faces

'''
Performs a validation, given a validator
'''
def validate(r, vname, fname):
    print(vname, fname)
    f = r.FILES.get(vname)
    print(f)
    v = Validator.objects.get(identifier=vname)
    if v.validator is None and v.pattern is None:
        return True
    elif (v.validator is None or len(v.validator) < 1) and (v.pattern is not None or len(v.pattern) > 0):
        ret = image_extractor(v.pattern, f)
        print(ret)
        if ret is not False:
            return True
        else:
            return False
    elif (v.validator is not None or len(v.validator) > 0) and (v.pattern is not None or len(v.pattern) > 0):
        ex = image_extractor(r'' + v.pattern, f)
        if ex is not False:
            # post to the validator
            if v.identifier is not None:
                ctx = {
                    v.identifier: ex,
                } 
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
            else:
                ctx = {
                    f.name: ex
                } 
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
        else:
            return False
    elif v.validator is not None and v.pattern is None:
        if not v.internal:
            if v.identifier is not None:
                ctx = {
                    v.identifier: f,
                }
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
            else:
                ctx = {
                    f.name: f,
                }
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
        else:
            if 'userid' in vname:
                check_id
    else:
        return False