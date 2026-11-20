from django.db import models



class Module(models.Model): #in Django every database models inherit from models.Model
    name=models.CharField(max_length=100,unique=True)

    def _str_(self):  #self is similar to this in js,current role
        return self.name

class Permission(models.Model):
    module=models.ForeignKey(Module,on_delete=models.CASCADE,related_name="permissions")#one module can have many permissions,on deleteing that module permisisons related to it should also delete
    action=models.CharField(max_length=50) #create,edit,delete,view actions
    codename=models.CharField(max_length=100,unique=True) #usermanagmentview,to know whether a particular module have a permission
    #related names provides a reverse relationship to access the module

class Meta: #inner class says that one module can have different actions,but don't duplicate modules
    unique_together=("module","action")

    def __str__(self):
     return f"{self.module.name}-{self.action}"

class Role(models.Model):
    name=models.CharField(max_length=100,unique=True)
    is_active=models.BooleanField(default=True)
    permissions=models.ManyToManyField(Permission,blank=True,related_name="roles")

def __str__(self):
        return self.name