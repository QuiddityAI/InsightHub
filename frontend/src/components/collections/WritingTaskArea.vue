<script setup>
import {
  TrashIcon,
} from "@heroicons/vue/24/outline"
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';
import Dropdown from 'primevue/dropdown';
import InputText from 'primevue/inputtext';
import InputGroup from 'primevue/inputgroup';
import Dialog from "primevue/dialog";
import Textarea from 'primevue/textarea';
import SelectButton from 'primevue/selectbutton';

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
  props: ["collection_id", "class_name"],
  emits: [],
  data() {
    return {
      writing_task_ids: [],
      new_writing_task_name: '',
      item_selection_options: [
        {label: 'All Items', value: true},
        {label: 'Selected Items', value: false},
      ],
      show_used_prompt: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    references() {
      const task = this.appStateStore.selected_writing_task
      if (task && task.additional_results && task.additional_results.references) {
        let references = ''
        let i = 1
        for (const ds_and_item_id of task.additional_results.references) {
          references += `${i}. ${ds_and_item_id[0]}: ${ds_and_item_id[1]}\n`
          i += 1
        }
        return references
      }
      return ''
    },
    available_source_fields() {
      const available_fields = {}
      // for (const dataset of this.included_datasets) {
      //   for (const field of Object.values(dataset.object_fields)) {
      //     available_fields[field.identifier] = {
      //       identifier: field.identifier,
      //       name: field.description || field.identifier,
      //     }
      //   }
      // }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        name: 'Descriptive Text',
      }
      available_fields['_full_text_snippets'] = {
        identifier: '_full_text_snippets',
        name: 'Full Text Excerpts',
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
  },
  mounted() {
    this.get_writing_tasks()
  },
  watch: {
    'appStateStore.selected_writing_task_id'() {
      this.get_writing_task()
    },
    'appStateStore.selected_writing_task.use_all_items'() {
      if (this.appStateStore.selected_writing_task.use_all_items === null) {
        this.appStateStore.selected_writing_task.use_all_items = true
      }
    },
  },
  methods: {
    get_writing_tasks() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient.post(`/org/data_map/get_writing_tasks`, body)
      .then(function (response) {
        that.writing_task_ids = response.data
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_writing_task() {
      const that = this
      const body = {
        task_id: this.appStateStore.selected_writing_task_id,
      }
      httpClient.post(`/org/data_map/get_writing_task_by_id`, body)
      .then(function (response) {
        that.appStateStore.selected_writing_task = response.data
        if (that.appStateStore.selected_writing_task.is_processing) {
          setTimeout(() => {
            that.get_writing_task()
          }, 1000)
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    add_writing_task(name) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        name: name,
      }
      httpClient.post(`/org/data_map/add_writing_task`, body)
      .then(function (response) {
        const task = response.data
        task.module = 'openai_gpt_4_o'
        that.writing_task_ids.push({id: task.id, name: task.name})
        that.appStateStore.selected_writing_task_id = task.id
        that.appStateStore.selected_writing_task = task
        that.new_writing_task_name = ''
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    update_writing_task(on_success=null) {
      const that = this
      const task = this.appStateStore.selected_writing_task
      task.source_fields = ['_descriptive_text_fields']
      const body = {
        task_id: this.appStateStore.selected_writing_task_id,
        name: task.name,
        source_fields: task.source_fields,
        selected_item_ids: task.selected_item_ids,
        module: task.module,
        parameters: task.parameters,
        prompt: task.prompt,
        text: task.text,
      }
      httpClient.post(`/org/data_map/update_writing_task`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    delete_writing_task() {
      const that = this
      const body = {
        task_id: this.appStateStore.selected_writing_task_id,
      }
      httpClient.post(`/org/data_map/delete_writing_task`, body)
      .then(function (response) {
        that.writing_task_ids = that.writing_task_ids.filter((task) => task.id !== that.appStateStore.selected_writing_task_id)
        that.appStateStore.selected_writing_task = null
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    execute_writing_task() {
      const that = this
      this.update_writing_task(() => {
        const body = {
          task_id: this.appStateStore.selected_writing_task_id,
        }
        httpClient.post(`/org/data_map/execute_writing_task`, body)
        .then(function (response) {
          that.appStateStore.selected_writing_task.is_processing = true
          setTimeout(() => {
            that.get_writing_task()
          }, 1000)
        })
        .catch(function (error) {
          console.error(error)
        })
      })
    },
    convert_to_html(text) {
      // escape html
      text = text.replace(/&/g, "&amp;")
      text = text.replace(/</g, "&lt;")
      text = text.replace(/>/g, "&gt;")
      // convert newlines to <br>
      return text.replace(/(?:\r\n|\r|\n)/g, '<br>')
    },
  },
}
</script>

<template>
  <div class="ml-4 flex flex-col gap-2">

    <div class="flex w-2/3 flex-row items-center justify-center">
      <InputGroup>
        <InputText placeholder="New Writing Task" v-model="new_writing_task_name" />
        <Button label="Add" @click="add_writing_task(new_writing_task_name)"></Button>
      </InputGroup>
    </div>
    <Dropdown
      v-model="appState.selected_writing_task_id"
      :options="writing_task_ids"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Writing Task..."
      class="mt-2 w-full h-8 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />

    <div v-if="appState.selected_writing_task" class="flex-1 flex flex-col gap-2 overflow-y-auto">

      <div class="flex flex-row">
        Prompt:
        <div class="flex-1"></div>
        <button
          @click="delete_writing_task()"
          v-tooltip.left="{ value: 'Delete Writing Task', showDelay: 500 }"
          class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>
      </div>

      <textarea v-model="appState.selected_writing_task.prompt" placeholder="prompt"
        class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      <div class="flex flex-row gap-2 items-center">
        <div class="flex-1 min-w-0">
          <MultiSelect v-model="appState.selected_writing_task.source_fields"
            :options="available_source_fields"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Sources..."
            :maxSelectedLabels="0"
            selectedItemsLabel="{0} Source(s)"
            class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
        <div class="flex-1 min-w-0">
          <Dropdown v-model="appState.selected_writing_task.module"
            :options="appState.available_ai_modules"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Module.."
            class="w-full h-full text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
      </div>

      <div class="flex flex-row gap-2">
        <SelectButton v-model="appState.selected_writing_task.use_all_items"
          :options="item_selection_options" optionLabel="label" optionValue="value"
          class="ml-[2px]" />
        <button @click="update_writing_task()" class="px-2 py-1 rounded bg-gray-100 hover:bg-blue-100/50">Update</button>
        <button @click="execute_writing_task()" class="px-2 py-1 rounded bg-green-100 hover:bg-blue-100/50">Run</button>
        <span v-if="appState.selected_writing_task.is_processing" class="text-sm text-gray-500">Processing...</span>
      </div>

      <textarea v-model="appState.selected_writing_task.text"
        class="flex-1 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"/>

      <textarea v-model="references" readonly
        class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"/>

      <div class="flex flex-row gap-2">
        <div class="flex-1"></div>
        <button v-if="appState.user.is_staff && appState.selected_writing_task.additional_results.used_prompt" @click="show_used_prompt = true"
          v-tooltip.right="{'value': 'Show the used prompt', showDelay: 500}"
          class="h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
          P
        </button>
        <Dialog v-model:visible="show_used_prompt" modal header="Used Prompt">
          <div class="overflow-y-auto max-h-[400px]"
            v-html="convert_to_html(appState.selected_writing_task.additional_results.used_prompt)" />
        </Dialog>
      </div>
    </div>
  </div>

</template>

<style scoped>
</style>
