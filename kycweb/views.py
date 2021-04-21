from django.http import request
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import UserForm, UsrForm, FileForm
from .models import BankingChestType, ChestRegistry, Chest, Usr, FileInstances, HitsRegistry, WorkChestType, Validator
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
import pathlib, os, sys, pytesseract, pdf2image, PIL, io, numpy, re, requests, json, Levenshtein as lev, datetime
from PIL import ImageEnhance, ImageOps

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
        return render(r, "kycweb/chest.html")

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
                chest_name="banking".format(r.POST.get("uname")), chest_size=0, created_by=usr)
            bnk_id = new_file(chest, r, "userid")
            bnk_kra = new_file(chest, r, "userkra")
            bnk_util = new_file(chest, r, "userutil")
            usr.addr      = r.POST.get("uaddress"), 
            usr.bdate     = r.POST.get("bd"), 
            usr.full_name =r.POST.get("uname").upper()
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

    def get(self, r, chest_id):
        chest = Chest.objects.get(chest_ID=chest_id)
        chest.delete()
        return redirect('/')

    def post(self, r, chest_id):
        chest = Chest.objects.get(chest_ID=chest_id)
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