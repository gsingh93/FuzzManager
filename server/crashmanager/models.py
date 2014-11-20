from django.db import models
from django.utils import timezone
from FTB.Signatures.CrashSignature import CrashSignature
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration

from django.core.files.storage import FileSystemStorage
import json

class Platform(models.Model):
    name = models.CharField(max_length=63)

class Product(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class OS(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class TestCase(models.Model):
    test = models.FileField(storage=FileSystemStorage(), upload_to="tests")
    size = models.IntegerField(default=0)
    quality = models.IntegerField(default=0)
    isBinary = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        # This variable can hold the testcase data temporarily
        self.content = None
        
        # For performance reasons we do not load the test here
        # automatically. You must call the loadTest method if you
        # want to access the test content
        
        super(TestCase, self).__init__(*args, **kwargs)
    
    def loadTest(self):
        self.test.open(mode='rb')
        self.content = self.test.read()
        self.test.close()
        
    def storeTestAndSave(self):
        self.size = len(self.content)
        self.test.open(mode='w')
        self.test.write(self.content)
        self.test.close()
        self.save()

class Client(models.Model):
    name = models.CharField(max_length=255)
    
class BugProvider(models.Model):
    classname = models.CharField(max_length=255, blank=False)
    hostname = models.CharField(max_length=255, blank=False)
    
    # This is used to annotate bugs with the URL linking to them
    urlTemplate = models.CharField(max_length=1023, blank=False)
    
    def getInstance(self):
        # Dynamically instantiate the provider as requested
        providerModule = __import__('crashmanager.Bugtracker.%s' % self.classname, fromlist=[self.classname])
        providerClass = getattr(providerModule, self.classname)
        return providerClass(self.pk, self.hostname)

class Bug(models.Model):
    externalId = models.CharField(max_length=255, blank=True)
    externalType = models.ForeignKey(BugProvider)
    
class Bucket(models.Model):
    bug = models.ForeignKey(Bug, blank=True, null=True)
    signature = models.TextField()
    shortDescription = models.CharField(max_length=1023, blank=True)
    
    def getSignature(self):
        return CrashSignature(self.signature)
    
    def save(self, *args, **kwargs):
        # Sanitize signature line endings so we end up with the same hash
        # TODO: We might want to just parse the JSON here, and re-serialize
        # it to a canonical string representation.
        self.signature = self.signature.replace(r"\r\n", r"\n")
        super(Bucket, self).save(*args, **kwargs)

class CrashEntry(models.Model):
    created = models.DateTimeField(default=timezone.now)
    platform = models.ForeignKey(Platform)
    product = models.ForeignKey(Product)
    os = models.ForeignKey(OS)
    testcase = models.ForeignKey(TestCase, blank=True, null=True)
    client = models.ForeignKey(Client)
    bucket = models.ForeignKey(Bucket, blank=True, null=True)
    rawStdout = models.TextField(blank=True)
    rawStderr = models.TextField(blank=True)
    rawCrashData = models.TextField(blank=True)
    metadata = models.TextField(blank=True)
    env = models.TextField(blank=True)
    args = models.TextField(blank=True)
    crashAddress = models.CharField(max_length=255, blank=True)
    shortSignature = models.CharField(max_length=255, blank=True)
    
    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.argsList = None
        self.envList = None
        self.metadataList = None
        
        # For performance reasons we do not deserialize these fields
        # automaticlly here. You need to explicitely call the 
        # deserializeFields method if you need this data.
        
        super(CrashEntry, self).__init__(*args, **kwargs)
        
        
    def save(self, *args, **kwargs):
        # Reserialize data, then call regular save method
        if self.argsList:
            self.args = json.dumps(self.argsList)
    
        if self.envList:
            envDict = dict([x.split("=", 1) for x in self.envList])
            self.env = json.dumps(envDict)
    
        if self.metadataList:
            metadataDict = dict([x.split("=", 1) for x in self.metadataList])
            self.metadata = json.dumps(metadataDict)
        
        super(CrashEntry, self).save(*args, **kwargs)
    
    def deserializeFields(self):
        if self.args:
            self.argsList = json.loads(self.args)
    
        if self.env:
            envDict = json.loads(self.env)
            self.envList = ["%s=%s" % (s,envDict[s]) for s in envDict.keys()]
    
        if self.metadata:
            metadataDict = json.loads(self.metadata)
            self.metadataList = ["%s=%s" % (s,metadataDict[s]) for s in metadataDict.keys()]
    
    
    def getCrashInfo(self):
        # TODO: This should be cached at some level
        # TODO: Need to include environment and program arguments here
        configuration = ProgramConfiguration(self.product.name, self.platform.name, self.os.name, self.product.version)
        return CrashInfo.fromRawCrashData(self.rawStdout, self.rawStderr, configuration, self.rawCrashData)
    
class BugzillaTemplate(models.Model):
    name = models.TextField()
    product = models.TextField()
    component = models.TextField()
    summary = models.TextField(blank=True)
    version = models.TextField()
    description = models.TextField(blank=True)
    whiteboard = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    op_sys = models.TextField(blank=True)
    platform = models.TextField(blank=True)
    priority = models.TextField(blank=True)
    severity = models.TextField(blank=True)
    alias = models.TextField(blank=True)
    cc = models.TextField(blank=True)
    assigned_to = models.TextField(blank=True)
    qa_contact = models.TextField(blank=True)
    target_milestone = models.TextField(blank=True)
    attrs = models.TextField(blank=True)

