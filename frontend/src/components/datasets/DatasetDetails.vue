<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import FileUpload from 'primevue/fileupload';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
import Badge from 'primevue/badge';
import Message from 'primevue/message';
import ProgressBar from 'primevue/progressbar';
import Checkbox from 'primevue/checkbox';

import CollectionItem from "../collections/CollectionItem.vue";
import SelectCollection from '../collections/SelectCollection.vue';

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
      add_to_collection: false,
      upload_in_progress: false,
      visible_area: "upload_files",
      upload_tasks: [],
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.selected_import_converter = this.dataset.schema.applicable_import_converters.length ? this.dataset.schema.applicable_import_converters[0] : null
    this.get_dataset_additional_info()
    this.get_upload_task_status()
  },
  watch: {
    'dataset.is_public'() {
      this.update_dataset()
    },
    'dataset.is_organization_wide'() {
      this.update_dataset()
    },
  },
  methods: {
    get_dataset_additional_info() {
      const that = this
      httpClient
        .post("/org/data_map/dataset", { dataset_id: this.dataset.id, additional_fields: ["item_count"]})
        .then(function (response) {
          // don't overwrite the whole dataset object as other fields need special handling
          that.dataset.item_count = response.data.item_count
        })
        .catch(function (error) {
          console.error(error)
        })
    },
    update_dataset() {
      const that = this
      const body = {
        dataset_id: that.dataset.id,
        updates: {
          is_public: that.dataset.is_public,
          is_organization_wide: that.dataset.is_organization_wide,
        },
      }
      httpClient.post(`/org/data_map/change_dataset`, body)
      .then(function (response) {
        that.$toast.add({severity:'success', summary: 'Success', detail: 'Dataset updated successfully.', life: 3000})
      })
      .catch(function (error) {
        console.error(error)
      })
    },
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
      const that = this
      if (!this.selected_import_converter) {
        this.$toast.add({severity:'error', summary: 'Error', detail: 'Please select an import type.'})
        return
      }
      // see https://github.com/primefaces/primevue/blob/master/components/lib/fileupload/FileUpload.vue
      let xhr = new XMLHttpRequest();
      let formData = new FormData();
      const fileUploaderComponent = this.$refs.fileUploader;
      // the original component calls clear() right after this custom upload method which removes the files array
      // we want to restore it after that:
      setTimeout(() => {
        fileUploaderComponent.files = event.files
      }, 10);

      fileUploaderComponent.$emit('before-upload', {
        xhr: xhr,
        formData: formData
      });

      formData.append("dataset_id", this.dataset.id);
      formData.append("import_converter", this.selected_import_converter.identifier);
      if (this.add_to_collection) {
        const collection_selection = this.$refs.collection_selection
        if (collection_selection.selected_collection_id) {
          formData.append("collection_id", collection_selection.selected_collection_id);
          formData.append("collection_class", collection_selection.selected_collection_class);
        }
      }

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
            const data = JSON.parse(xhr.responseText);
            if (data.errors) {
              for (let error of data.errors) {
                fileUploaderComponent.messages.push(error)
              }
            }
            that.get_upload_task_status()

            if (fileUploaderComponent.fileLimit) {
              fileUploaderComponent.uploadedFileCount += event.files.length;
            }

            fileUploaderComponent.$emit('upload', {
              xhr: xhr,
              files: event.files
            });
          } else {
            fileUploaderComponent.$emit('error', {
              xhr: xhr,
              files: event.files
            });
          }

          fileUploaderComponent.uploadedFiles.push(...event.files);
          fileUploaderComponent.clear();

          that.$toast.add({severity:'success', summary: 'Success', detail: 'Files uploaded successfully.', life: 3000})
          that.upload_in_progress = false
        }
      };

      xhr.open('POST', fileUploaderComponent.url, true);

      fileUploaderComponent.$emit('before-send', {
        xhr: xhr,
        formData: formData
      });

      xhr.withCredentials = fileUploaderComponent.withCredentials;

      xhr.send(formData);
      that.upload_in_progress = true
    },
    get_upload_task_status() {
      const that = this
      httpClient
        .post("/data_backend/upload_files/status", { dataset_id: this.dataset.id })
        .then(function (response) {
          that.upload_tasks = response.data
          // if any task is still in progress, check again in 500ms
          if (that.upload_tasks.filter(task => task.is_running).length > 0) {
            setTimeout(that.get_upload_task_status, 1000)
          } else {
            that.get_dataset_additional_info()
          }
        })
        .catch(function (error) {
          console.error(error)
        })
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
      <span class="font-normal text-gray-400" v-if="dataset.schema.name">({{ dataset.schema.name }})</span>
      <div class="flex-1"></div>
      <button
          @click="appState.show_global_map([dataset.id])"
          title="Show all items (or a representative subset if there are too many)"
          class="ml-1 rounded-md px-2 h-7 text-sm text-gray-500 bg-gray-100 hover:bg-blue-100/50">
          {{ dataset.item_count < 2000 ? 'Show all items' : 'Show representative overview' }}
        </button>
      <button
        v-if="dataset.admins?.includes(appState.user.id)"
        @click="delete_dataset"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <div class="flex flex-col ml-2 mb-4 mt-2 gap-1">
      <p class="text-gray-600 text-sm">
        Items in this dataset: <b>{{ dataset.item_count !== undefined ? dataset.item_count.toLocaleString() : 'unknown' }}</b>
      </p>
      <div>

      </div>
      <div class="flex flex-col gap-2">
        <label class="flex items-center" v-if="appState.user.is_staff || dataset.is_public">
          <input type="checkbox" v-model="dataset.is_public" :disabled="!dataset.admins?.includes(appState.user.id) || !appState.user.is_staff">
          <span class="ml-2 text-sm text-gray-600">Public for everyone on the internet {{ !appState.user.is_staff ? '(can only be changed by staff)': '' }}</span>
        </label>
        <label class="flex items-center">
          <input type="checkbox" v-model="dataset.is_organization_wide" :disabled="!dataset.admins?.includes(appState.user.id)">
          <span class="ml-2 text-sm text-gray-600">Available to other organization members</span>
        </label>
      </div>
    </div>

    <div v-if="dataset.admins?.includes(appState.user.id)">
      <button class="w-full hover:bg-gray-100" @click="visible_area = 'upload_files'">
        <h3 class="text-left text-md text-gray-600 font-semibold">
          Upload Files
        </h3>
      </button>
      <div v-if="visible_area == 'upload_files'" class="ml-2 mb-3 mt-2 flex flex-col gap-2">
        <div class="flex flex-row items-center">
          <label class="mr-2 text-sm text-gray-700" for="import_type">Import Type:</label>
          <Dropdown
            id="import_type"
            v-model="selected_import_converter"
            :options="dataset.schema.applicable_import_converters"
            optionLabel="display_name"
            placeholder="Select an import type"/>
        </div>
        <div v-if="selected_import_converter?.description" class="ml-3 mr-2 mb-2 text-sm text-gray-500"
          v-html="selected_import_converter?.description.replaceAll('\n', '<br>')">
        </div>
        <div v-if="selected_import_converter?.example_file_url" class="ml-3 mr-2 mb-2 text-sm text-gray-500">
          <a :href="selected_import_converter.example_file_url" target="_blank" class="text-blue-500">Example file</a>
        </div>
        <div class="flex flex-row items-center">
          <label class="mr-2 text-sm text-gray-700" for="target_collection">
            Add to Collection (optional):
          </label>
          <Checkbox v-model="add_to_collection" :binary="true" class="mr-2"></Checkbox>
          <SelectCollection v-show="add_to_collection" ref="collection_selection">
          </SelectCollection>
        </div>
        <FileUpload
          v-if="selected_import_converter"
          ref="fileUploader"
          name="files[]"
          url="/data_backend/upload_files"
          :multiple="true"
          :maxFileSize="10000000000"
          :fileLimit="500"
          customUpload
          @uploader="custom_file_uploader"
          >
          <template #content="{ files, uploadedFiles, removeFileCallback, messages, progress, onMessageClose }">
            <div v-if="files.length > 0 || upload_in_progress">
              <div class="flex flex-col gap-1">
                <span v-if="files.length > 0" class="text-gray-700">Selected files: {{ files.length }} </span>
                <ProgressBar v-if="progress > 0" :value="progress" :showValue="false" />
                <Message v-for="msg of messages" :key="msg" severity="error" @close="onMessageClose">{{ msg }}</Message>
                <div v-for="(file, index) of files" :key="file.name + file.type + file.size" class="card m-0 px-2 flex flex-row justify-between items-center gap-1">
                  <span class="max-w-[350px] font-semibold break-words">{{ file.name }}</span>
                  <div class="flex-1"></div>
                  <Badge value="Waiting" severity="warning" class="flex-none w-14" />
                  <Button label="X" @click="removeFileCallback(index)" outlined rounded  severity="danger" />
                </div>
              </div>
            </div>
            <div v-if="upload_in_progress" class="mt-2">
              <p class="text-gray-700">Uploading files...</p>
            </div>

            <div v-if="uploadedFiles.length > 0">
              <span class="text-gray-700">Uploaded files: {{ uploadedFiles.length }} </span>
              <!-- <div class="flex flex-col gap-1">
                <div v-for="(file, index) of uploadedFiles" :key="file.name + file.type + file.size" class="card m-0 px-2 flex flex-row justify-between items-center gap-1">
                  <span class="font-semibold">{{ file.name }}</span>
                  <div class="flex-1"></div>
                  <Badge value="Completed" severity="success" class="flex-none w-18" />
                  <Button label="X" @click="removeUploadedFileCallback(index)" outlined rounded  severity="danger" />
                </div>
              </div> -->
            </div>
          </template>
          <template #empty>
            <div v-if="!upload_in_progress">
              <p class="text-sm text-gray-600">Drag and drop files here to upload.<br><br>
                You can upload individual files or .zip / .tar.gz archives containing multiple files.
              </p>
            </div>
          </template>
        </FileUpload>

        <p v-if="upload_tasks.length !== 0" class="text-gray-700">
          Recent uploads:
        </p>

        <div v-for="task in upload_tasks" :key="task.task_id" class="py-1 px-2 rounded-md border-2 border-gray-100">
          <p class="text-gray-700">
            Status: {{ task.status }} ({{ (task.progress * 100).toFixed(0) }}%)
          </p>
          <p v-if="task.failed_files.length !== 0" class="text-red-700">
            Some files could not be processed ({{ task.failed_files.length }} errors in total):
          </p>
          <ul role="list" class="mt-1 text-sm">
            <li
              v-for="failure in task.failed_files"
              :key="failure.filename"
              class="justify-between pb-3">
              <span class="text-red-700">{{ failure.filename }}</span><br>
              <span class="text-gray-500">{{ failure.reason }}</span>
            </li>
          </ul>
          <p v-if="task.inserted_ids.length !== 0" class="text-gray-700 text-sm">
            Items successfully uploaded: {{ task.inserted_ids.length }} (showing max. 10)<br>
            Duration: {{ (((new Date(task.finished_at)).getTime() - (new Date(task.started_at)).getTime()) / (60*1000)).toFixed(1) }} min
          </p>
          <ul role="list" class="mt-1">
            <li
              v-for="ds_and_item_id in task.inserted_ids.slice(0, 10)"
              :key="ds_and_item_id.join('_')"
              class="justify-between pb-3">
              <CollectionItem
                :dataset_id="ds_and_item_id[0]"
                :item_id="ds_and_item_id[1]"
                :is_positive="true"
                :show_remove_button="false">
              </CollectionItem>
            </li>
          </ul>
        </div>

      </div>
      <button v-if="appState.dev_mode" class="mt-2 w-full hover:bg-gray-100" @click="visible_area = 'upload_using_api'">
        <h3 class="text-left text-md text-gray-600 font-semibold">
          Upload using API
        </h3>
      </button>
      <div v-if="visible_area == 'upload_using_api'" class="ml-2">
        <p class="mt-2 mb-1 text-gray-700">
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
