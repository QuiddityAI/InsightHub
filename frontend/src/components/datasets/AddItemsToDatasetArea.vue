<script setup>
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

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
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
  props: ["schema", "target_collection", "target_collection_class", "preselected_import_converter", "dataset_id"],
  emits: ["items_added"],
  data() {
    return {
      selected_import_converter: this.preselected_import_converter,
      add_to_collection: false,
      upload_in_progress: false,
      upload_tasks: [],
      actual_dataset_id: this.dataset_id,
      manually_created_item: {},
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.selected_import_converter = this.schema.applicable_import_converters.length ? this.schema.applicable_import_converters[0] : null
    this.get_upload_task_status()
  },
  watch: {
    schema() {
      this.selected_import_converter = this.schema.applicable_import_converters.length ? this.schema.applicable_import_converters[0] : null
    },
  },
  methods: {
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

      formData.append("dataset_id", this.dataset_id);
      formData.append("schema_identifier", this.schema.identifier);
      formData.append("user_id", this.appStateStore.user.id);
      formData.append("organization_id", this.appStateStore.organization.id);
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
            that.set_actual_dataset_id(data.dataset_id)
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
    set_actual_dataset_id(dataset_id) {
      this.actual_dataset_id = dataset_id
      if (!this.appStateStore.datasets[dataset_id]) {
        this.appStateStore.fetch_dataset(dataset_id)
      }
    },
    get_upload_task_status() {
      const that = this
      if (!this.actual_dataset_id || this.actual_dataset_id === -1) {
        return
      }
      httpClient
        .post("/data_backend/upload_files/status", { dataset_id: this.actual_dataset_id })
        .then(function (response) {
          that.upload_tasks = response.data
          // if any task is still in progress, check again in 500ms
          if (that.upload_tasks.filter(task => task.is_running).length > 0) {
            setTimeout(that.get_upload_task_status, 1000)
          } else {
            that.$emit('items_added')
          }
        })
        .catch(function (error) {
          console.error(error)
        })
    },
    manually_create_item() {
      const that = this
      const collection_id = this.target_collection?.id
      const collection_class = this.target_collection_class
      if (this.add_to_collection) {
        const collection_selection = this.$refs.collection_selection
        if (collection_selection.selected_collection_id) {
          collection_id = collection_selection.selected_collection_id
          collection_class = collection_selection.selected_collection_class
        }
      }
      const body = {
        dataset_id: this.dataset_id,
        schema_identifier: this.schema.identifier,
        user_id: this.appStateStore.user.id,
        organization_id: this.appStateStore.organization.id,
        import_converter: this.selected_import_converter.identifier,
        collection_id: collection_id,
        collection_class: collection_class,
        items: [this.manually_created_item],
      }
      httpClient
        .post("/data_backend/import_items", body)
        .then(function (response) {
          that.set_actual_dataset_id(response.data.dataset_id)
          that.get_upload_task_status()
        })
        .catch(function (error) {
          console.error(error)
        })
      this.manually_created_item = {}
    },
  },
}
</script>

<template>
  <div class="mb-3 mt-2 flex flex-col gap-2">
    <div class="flex flex-row items-center">
      <Dropdown
        id="import_type"
        v-model="selected_import_converter"
        :options="schema.applicable_import_converters"
        optionLabel="display_name"
        placeholder="Select an import type"/>
    </div>
    <div v-if="selected_import_converter?.description" class="ml-3 mr-2 mb-2 text-sm text-gray-500"
      v-html="selected_import_converter?.description.replaceAll('\n', '<br>')">
    </div>
    <div v-if="selected_import_converter?.example_file_url" class="ml-3 mr-2 mb-2 text-sm text-gray-500">
      <a :href="selected_import_converter.example_file_url" target="_blank" class="text-blue-500">Example file</a>
    </div>
    <div v-if="!target_collection" class="flex flex-row items-center">
      <label class="mr-2 text-sm text-gray-700" for="target_collection">
        Add to Collection (optional):
      </label>
      <Checkbox v-model="add_to_collection" :binary="true" class="mr-2"></Checkbox>
      <SelectCollection v-show="add_to_collection" ref="collection_selection">
      </SelectCollection>
    </div>
    <div v-if="selected_import_converter && selected_import_converter.manual_insert_form?.length">
      <div v-for="field in selected_import_converter.manual_insert_form">
        <label :for="field.identifier" class="mr-2 text-sm text-gray-700">{{ field.label }}:</label>
        <input :id="field.identifier" v-model="manually_created_item[field.identifier]" class="border border-gray-300 rounded-md p-1">
      </div>
      <button @click="manually_create_item()">Create Item</button>
    </div>
    <FileUpload
      v-if="selected_import_converter && !selected_import_converter.manual_insert_form?.length"
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

</template>

<style scoped>
</style>
