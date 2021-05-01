from json.encoder import JSONEncoder
from django.http import request
from django.http.response import Http404
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from face_recognition.api import face_locations
from .forms import UserForm, UsrForm, FileForm
from .models import BankingChestType, ChestRegistry, Chest, Corporation, Usr, FileInstances, HitsRegistry, WorkChestType, Validator
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
import pathlib, os, sys, pytesseract, pdf2image, PIL, io, numpy, re, requests, json, Levenshtein as lev, datetime, face_recognition
from PIL import ImageEnhance, ImageOps
from django.conf import settings

LIMIT = 100000000

'''
Uploading files from user to 
destination folder
'''
def upload_file(f, d):
    with open(d, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

'''
Creating both the default and extended
user
'''
def create_user(r):
    registered = False
    if r.method == "POST":
        user_form = UserForm(data=r.POST)
        usr_f = UsrForm(data=r.POST)

        if user_form.is_valid() and usr_f.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            usr = usr_f.save(commit=False)
            usr.def_usr = user

            if 'profile_pic' in r.FILES:
                usr.profile_pic = r.FILES['profile_pic']

            usr.save()
            registered = True
            return redirect('/login')
        else:
            print(user_form.errors, usr_f.errors)
    else:
        user = UserForm()
        usr = UsrForm

    return render(r, 'registration/signup', {'reg': registered})

'''
The contact location/ dashboard where users
view information like available space the
chests they've created and links that they can create
'''
@login_required
def home(r):
    return render(r, 'kycweb/dash.html')


'''
Loads chest data & information and renders chests UI
'''
@login_required
def chests(r):
    n_chests = n_hits = n_size = 0
    dng = False
    usr = Usr.objects.get(def_usr=r.user.id)
    chests = Chest.objects.filter(created_by=usr.id)
    n_hits = HitsRegistry.objects.filter(usr__id=r.user.id).count()
    n_chests = chests.count()
    if n_chests>0:
        for i in chests:
            n_size += int(i.chest_size)/1000000
    else:
        n_size = n_size
    if (n_size/LIMIT)*100 <= 5 and (n_size/LIMIT)*100 > 0 and n_size>1:
        dng = True
    return render(r, 'kycweb/chests.html', {'chests':chests, 
                                          'n_chests':n_chests, 
                                          'size':n_size, 
                                          'lim':LIMIT/1000000,
                                          'dng': dng,
                                          'n_hits': n_hits
                                          })
# single chest instance view
@login_required
def chest(r):
    pass

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
        return fi
    else:
        fis = []
        for ft in r.FILES:
            fa = r.FILES.get(ft)
            up = c.chest_dir + '/' + fa.name
            fs = FileSystemStorage(location=c.chest_dir)
            fs.save(fa.name, fa)
            ft = pathlib.Path(fa.name).suffix
            fis.append(FileInstances.objects.create(chest=c, upload_path=up, file_type=file_type(ft)))
        return fis

'''
get image data depending on the file type
'''
def file_contents(f):
    f.seek(0)
    fc = f.read()
    ft = file_type(pathlib.Path(f.name).suffix)
    if ft == "document":
        pages = pdf2image.convert_from_bytes(fc)
        for pg in pages:
            pg = pg.convert('RGBA')
            dt = numpy.array(pg)
            dt = PIL.Image.fromarray(dt)

'''
Extract an RE pattern from image if it can
'''
def image_extractor(ptn, fa):
    fa.seek(0)
    fc = fa.read()
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
            pg.show()
            txt = pytesseract.image_to_string(pg)
            dct = dct + txt + "\n"
        idn = re.search(ptn, dct)
        if idn:
            return idn.group()
        else:
            return False
    if ft == "image":
        img = PIL.Image.open(io.BytesIO(fc))
        img = img.convert('RGBA')
        data = numpy.array(img)
        red, green, blue, alpha = data.T
        black_to_gray = (red > 140) & (blue > 130) & (green > 128)
        data[..., :-1][black_to_gray.T] = (255, 255, 255) 
        img = PIL.Image.fromarray(data)
        img.show()
        txt = pytesseract.image_to_string(img)
        idn = re.search(ptn, txt)
        if idn:
            return idn.group()
        else:
            return False

'''
Get a bearer token for the searches
'''
def get_bearer_token():
    data = {
        "username": "8448779624",
        "password": "qbHfd0CuiElByORb2VSkw55fTnXRHPlN"
    }
    headers = {
        "Authorization": "Basic TENkRjdjd2RWclN3YmtOOVppNUdyd2ZNRTNDSVFveUU6VnM3a3dwemVaVjRwSklBbA=="
    }
    r = requests.post("https://sandbox.jengahq.io/identity-test/v2/token/", data=data, headers=headers)
    print(r)
    return r

'''
Accepts ID uploads and checks their validity, ext of new file
'''
def check_id(r):
    fa = r.FILES.get("userid")
    idn = image_extractor(r'[0-9]{8}', fa)
    uname = image_extractor(r"(FULL NAMES)[ |\n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    if uname is False:
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    bday = image_extractor(r'(DATE OF BIRTH)[ |\n]*[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', fa)
    bday = re.search(r'[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', bday).group()
    print(r.POST.get("bd"))
    if idn:
        headers = {
            "Authentication": str(get_bearer_token())
        }
        data = {
            "id": "34938447"
        }
        ro = requests.post("https://sandbox.jengahq.io/identity-test/v2/token", headers=headers, data=data).json()
        if lev.distance(uname, r.POST.get("uname").upper()) < 7:
            dtb = datetime.datetime.strptime(r.POST.get("bd"), '%Y-%m-%d').strftime('%d.%m.%y')
            print(dtb) 
            if lev.distance(bday, dtb) < 7:
                ctx = {
                    'verified': True,
                }
            else:
                ctx = {
                    'verified': False,
                }
        else:
            ctx = {
                'verified': False
            }
        return JsonResponse(ctx)
    else:
        print(idn)
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)

'''
Accept KRA files and checks their validity
'''
def check_kra(r):
    fa = r.FILES.get("userkra")
    idn = image_extractor(r'[A-G][0-9]{9}[A-G]', fa)
    uname = image_extractor(r"(Taxpayer Name)[ \n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    if uname is False:
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    addr_check = []
    addr_check.append(image_extractor(i, fa) for i in r.POST.get("uaddress").split())
    for i in addr_check:
        count = 0
        if i is False:
            count+=1
        if count > 3:
            ctx = {
                'verified': False
            }
            return JsonResponse(ctx)
    print(uname)
    if idn:
        print(idn)
        if lev.distance(uname, r.POST.get("uname").upper()) < 7:
            ctx = {
                'verified': True,
            }
        else:
            ctx = {
                'verified': False
            }
        return JsonResponse(ctx)
    else:
        ctx = {
            'verified': False
        }
        return JsonResponse(ctx)

'''
Checks passport photos relative to the id_pic
decides validity based on distance
'''
def check_pic(r):
    id = r.FILES.get("userid")
    pic = r.FILES.get("pic")
    id.seek(0)
    pic.seek(0)
    img1 = PIL.Image.open(io.BytesIO(id.read()))
    img1 = img1.convert('RGBA')
    img2 = PIL.Image.open(io.BytesIO(pic.read()))
    img2 = img2.convert('RGBA')
    locs1 = face_recognition.face_locations(img1)
    locs2 = face_recognition.face_locations(img2)
    encs1 = face_recognition.face_encodings(img1, locs1)
    encs2 = face_recognition.face_encodings(img2, locs2)

    for enc in encs1:
        dis = face_recognition.face_distance(encs2, enc)
        print(dis)

    return HttpResponse("Hello")
    
'''
All file manipulation semantics
'''
class FileOperations():

    def delete_file(r, fid):
        f = FileInstances.objects.get(pk=fid)
        os.remove(f.upload_path)
        c = f.chest
        if c.auth_chest:
            ac = None
            try:
                ac = BankingChestType.objects.get(abstract_chest=c)
            except:
                try:
                    ac = WorkChestType.objects.get(abstract_chest=c)
                except:
                    ac = None
            if ac is not None:
                f.delete()
                lv = ac.gen_auth_level()
                ctx = {"deleted": True, "level":lv}
                return JsonResponse(ctx)
            else:
                return Http404
    
    def create_file(r):
        pass

    def download_file(r, fid):
        f = FileInstances.objects.get(pk=fid)
        file_path = os.path.join(settings.BASE_DIR, f.upload_path)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fa:
                if f.file_type is 'document':
                    rsp = HttpResponse(fa.read(), content_type="application/pdf")
                else:
                    ft = pathlib.Path(fa.name).suffix[1:]
                    rsp = HttpResponse(fa.read(), content_type="image/" + ft)
                rsp['Content-Disposition'] = 'inline; filename=' + f.get_file_name()
                return rsp
        return Http404

'''
New chest post form loader
'''
class ChestCreateView(LoginRequiredMixin, generic.View):
    model = FileInstances
    fileformclass = FileForm
    login_url = 'login/'   

    def get(self, r):
        fileform = self.fileformclass(None)
        return render(r, 'kycweb/new_chest.html', {'form': fileform})

    def post(self, r):
        chest_type = r.POST.get('chest-types')
        if chest_type == "oth":
            usr = Usr.objects.get(def_usr=r.user.id)
            chest = Chest.objects.create(chest_name=r.POST.get('chest-name'), chest_size=0, created_by=usr)
            nfls = int(r.POST.get('size-flag'))
            for i in range(0, nfls):
                new_file(chest, r)
        if chest_type is "bnk":
            requests.post("new_chest/bnk/", data=r)
        if chest_type is "bnk":
            requests.post("new_chest/wrk/", data=r)
        return redirect("/")

'''
Chest view loader
'''
class ChestView(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        files = FileInstances.objects.filter(chest=chest)
        usrs = ChestRegistry.objects.filter(chest=chest)
        authc = None
        if chest.auth_chest:
            try:
                authc = BankingChestType.objects.get(abstract_chest=chest)
            except:
                try:
                    authc = WorkChestType.objects.get(abstract_chest=chest)
                except:
                    chest.auth_chest = False
        ctx = {
            "chest": chest,
            "files": files,
            "users": usrs,
            "ac": authc
        }
        return render(r, "kycweb/chest.html", ctx)

    def extend_auth(r,c):
        pass

    def extend_chest(r):
        chest = Chest.objects.get(pk=r.POST.get("chest"))
        ctx = {
            "files": new_file(chest, r)
        }
        return render(r, "kycweb/files.html" ,ctx)

    def get_indiv_perm(r, pid):
        perm = ChestRegistry.objects.get(pk=pid)
        if perm.corporation is not None:
            print(perm.corporation.name)
        ctx = {
            "u": perm,
        }
        return render(r, "kycweb/perm.html", ctx)

    def change_permissions(r, reg_id):
        reg = ChestRegistry.objects.get(pk=reg_id)
        if reg.access:
            reg.access = False
        else:
            reg.access = True
        reg.save()
        ctx = {"state": reg.access}
        return JsonResponse(ctx)

    def remove_permissions(r, reg_id):
        reg = ChestRegistry.objects.get(pk=reg_id)
        reg.delete()
        ctx = {"deleted": True}
        return JsonResponse(ctx)

    def add_permissions(r, uid):
        u = c = None
        try:
            u = Usr.objects.get(ctx_id=uid)
        except:
            print("Not a user")
        try:
            c = Corporation.objects.get(key=uid)
        except:
            print("Not a corporation")
        ch = Chest.objects.get(chest_ID=r.POST.get('chest'))
        if ch is not None:
            if u is not None and c is None:
                cr = ChestRegistry.objects.create(usr=u, chest=ch, access=True)
                ctx = {"registry":cr.id}
                return JsonResponse(ctx)
            elif u is None and c is not None:
                cr = ChestRegistry.objects.create(corporation=c, chest=ch, access=True)
                ctx = {"registry":cr.id}
                return JsonResponse(ctx)
            elif u is not None and c is not None:
                ctx = {"error": "There was an issue creating this permission"}
                return JsonResponse(ctx)
            else:
                ctx = {"error": "This user/corporation does not exist"}
                return JsonResponse(ctx)
        else:
            ctx = {"error": "The was an issues processing this request"}

'''
New Banking auth instance. This 
only exists as a generic implementation
and extention of the ChestCreateView 
'''
class BankingChestCreateView(LoginRequiredMixin, generic.View):
    models = BankingChestType
    login_url = 'login/'

    def post(self, r):
        # by the time the view is at this point 
        # all docs have been verified to an extent
        usr = Usr.objects.get(def_usr=r.user.id)
        chest_type = r.POST.get('chest-types')
        if chest_type == "bnk":
            print(chest_type)
            chest = Chest.objects.create(
                chest_name="banking".format(r.POST.get("uname")), chest_size=0, created_by=usr, auth_chest=True, application='banking')
            bnk_id = new_file(chest, r, "userid")
            bnk_kra = new_file(chest, r, "userkra")
            bnk_util = new_file(chest, r, "userutil")
            usr.addr      = r.POST.get("uaddress"), 
            usr.bdate     = r.POST.get("bd"), 
            usr.full_name =r.POST.get("uname").upper()
            usr.save()
            b = BankingChestType.objects.create(
                abstract_chest=chest, bnk_id=bnk_id, kra=bnk_kra, utility=bnk_util)
            b.gen_auth_level()
            return redirect("/")

'''
New Work auth instance. This 
only exists as a generic implementation
and extention of the ChestCreateView as well. 
'''
class WorkChestCreateView(LoginRequiredMixin, generic.View):
    models = WorkChestType
    login_url = 'login/'

    def post(self, r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chest_type = r.POST.get('chest-types')
        if chest_type is "wrk":
            chest = Chest.objects.create(
                chest_name="wrk-".format(r.POST.get("uname")), chest_size=0, created_by=usr)
            wrk_id = new_file(chest, r, "userid")
            wrk_kra = new_file(chest, r, "userkra")
            wrk_nhif = new_file(chest, r, "usernhif")
            wrk_nssf = new_file(chest, r, "usernssf")
            cogc = new_file(chest, r, "cogc")
            WorkChestType.objects.create(
                abstract_chest=chest, wrk_id=wrk_id, kra=wrk_kra, nhif=wrk_nhif, nssf=wrk_nssf, cogc=cogc)
            return redirect("/")

'''
Delete chest view, has to somehow track
if the chest has any generic extentions
'''
class DeleteChest(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        chest.delete()
        return redirect('/')

    def post(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        chest.delete()
        return redirect('/')

'''
Search auth level
'''
class AuthLevelSearch(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chest = Chest.objects.get()

'''
Performs a validation, given a validator
'''
def validate(r, vname, fname):
    f = r.POST.get(fname)
    v = Validator.objects.get(name=vname)
    if v.validator is None and v.pattern is None:
        return True
    elif v.validator is None and v.pattern is not None:
        if image_extractor(v.pattern, f) is not False:
            return True
        else:
            return False
    elif v.validator is not None and v.pattern is not None:
        ex = image_extractor(v.pattern, f)
        if ex is not False:
            # post to the validator
            if v.identifier is not None:
                ctx = {
                    v.identifier: ex
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
        if v.identifier is not None:
            ctx = {
                v.identifier: f
            }
            r = requests.post(v.validator, data=ctx)
            if r.status_code == 200:
                return True
            else:
                return False
        else:
            ctx = {
                f.name: f
            }
            r = requests.post(v.validator, data=ctx)
            if r.status_code == 200:
                return True
            else:
                return False
    else:
        return False


'''
Creates a generic validator
'''
class ValidatorCreateView(generic.View):

    def get(self, r):
        # it'll return renderable create view
        pass

    def post(self, r):
        if r.POST.get('validator_name') is None:
            return redirect('/')
        Validator.objects.create(
            name = r.POST.get('validator_name'),
            validator = r.POST.get('validator'),
            pattern = r.POST.get('pattern'),
            identifier = r.POST.get('identifier')
        )

'''
'''