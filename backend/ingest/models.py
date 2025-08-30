from django.db import models

class UploadedFileWithHash(models.Model):
    user_id = models.IntegerField()
    dataset_id = models.IntegerField()
    md5 = models.CharField(max_length=32)
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File {self.filename} (User {self.user_id}, Dataset {self.dataset_id})"