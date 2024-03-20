<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import FileUpload from 'primevue/fileupload';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["dataset"],
  emits: ["close"],
  data() {
    return {
      selected_import_converter: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    delete_dataset() {
      if (!this.dataset.created_in_ui) {
        this.$toast.add({severity:'info', summary: 'Info', detail: 'You cannot delete this dataset because it was not created from the UI. Use the backend to delete it.'})
        return
      }
      if (!confirm("Are you sure you want to delete this dataset and all of its data? This action cannot be undone.")) {
        return
      }
      const that = this
      const body = {
        dataset_id: that.dataset.id,
      }
      httpClient.post(`/org/data_map/delete_dataset`, body)
      .then(function (response) {
        delete that.appStateStore.datasets[that.dataset.id]
        that.$emit("close")
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    async custom_file_uploader(event) {
      if (!this.selected_import_converter) {
        this.$toast.add({severity:'error', summary: 'Error', detail: 'Please select an import type.'})
        return
      }
      // see https://github.com/primefaces/primevue/blob/master/components/lib/fileupload/FileUpload.vue
      let xhr = new XMLHttpRequest();
      let formData = new FormData();
      const fileUploaderComponent = this.$refs.fileUploader;

      fileUploaderComponent.$emit('before-upload', {
        xhr: xhr,
        formData: formData
      });

      formData.append("dataset_id", this.dataset.id);
      formData.append("import_converter_id", this.selected_import_converter.id);

      for (let file of event.files) {
        formData.append(fileUploaderComponent.name, file, file.name);
      }

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          fileUploaderComponent.progress = Math.round((event.loaded * 100) / event.total);
        }

        fileUploaderComponent.$emit('progress', {
          originalEvent: event,
          progress: this.progress
        });
      });

      xhr.onreadystatechange = () => {
        if (xhr.readyState === 4) {
          fileUploaderComponent.progress = 0;

          if (xhr.status >= 200 && xhr.status < 300) {
            if (fileUploaderComponent.fileLimit) {
              fileUploaderComponent.uploadedFileCount += fileUploaderComponent.files.length;
            }

            fileUploaderComponent.$emit('upload', {
              xhr: xhr,
              files: fileUploaderComponent.files
            });
          } else {
            fileUploaderComponent.$emit('error', {
              xhr: xhr,
              files: fileUploaderComponent.files
            });
          }

          fileUploaderComponent.uploadedFiles.push(...fileUploaderComponent.files);
          fileUploaderComponent.clear();
        }
      };

      xhr.open('POST', fileUploaderComponent.url, true);

      fileUploaderComponent.$emit('before-send', {
        xhr: xhr,
        formData: formData
      });

      xhr.withCredentials = fileUploaderComponent.withCredentials;

      xhr.send(formData);
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ dataset.name }}</span>
      <div class="flex-1"></div>
      <button
        v-if="dataset.admins?.includes(appState.user.id)"
        @click="delete_dataset"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <div v-if="dataset.admins?.includes(appState.user.id)">
      <h3 class="text-md text-gray-600 font-semibold">
        Upload Files
      </h3>
      <div class="ml-2 mb-3 mt-2 flex flex-col gap-2">
        <label class="mr-2 text-sm text-gray-700" for="import_type">Import Type:</label>
        <Dropdown
          id="import_type"
          v-model="selected_import_converter"
          :options="dataset.applicable_import_converters"
          optionLabel="name"
          placeholder="Select an import type"/>
        <FileUpload
          ref="fileUploader"
          name="files[]"
          url="/data_backend/upload_files"
          :multiple="true"
          :maxFileSize="100000000"
          :fileLimit="500"
          customUpload
          @uploader="custom_file_uploader"
          >
          <template #empty>
            <p>Drag and drop files to here to upload.<br>
              You can upload individual files or zip files with multiple files.
            </p>
          </template>
        </FileUpload>
      </div>
      <h3 class="text-md text-gray-600 font-semibold">
        Upload using API
      </h3>
      <div class="ml-2">
        <p class="mb-1 text-gray-700">
          You can use the following command to upload data to this dataset:
        </p>
        <code class="text-sm text-gray-500 font-mono">
          curl "/api/datasets/{{ dataset.id }}/insert_many/" -X POST -H "Authorization: Bearer &lt;your_token&gt;" -H "Content-Type: application/json" -d '{"data": [{"name": "John Doe", "age": 30}, {"name": "Jane Doe", "age": 25}]}'
        </code>
      </div>
    </div>

    <div v-if="!dataset.admins?.includes(appState.user.id)">
      <span class="text-sm text-gray-500">
        You can't upload files to this dataset because you are not an admin.
      </span>
    </div>
  </div>
</template>

<style scoped>
</style>
