<script setup>
import {
  TrashIcon,
  PencilIcon,
  BackwardIcon,
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
import Message from "primevue/message";
 import {marked} from "marked";

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
      collection: useAppStateStore().collections.find((collection) => collection.id === this.collection_id),
      writing_task_ids: [],
      new_writing_task_name: '',
      item_selection_options: [
        {label: 'All Items', value: true},
        {label: 'Selected Items', value: false},
      ],
      edit_mode: false,
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
      //   for (const field of Object.values(dataset.schema.object_fields)) {
      //     available_fields[field.identifier] = {
      //       identifier: field.identifier,
      //       name: field.name || field.identifier,
      //     }
      //   }
      // }
      for (const column of this.collection.columns) {
        available_fields[column.identifier] = {
          identifier: '_column__' + column.identifier,
          name: column.name,
        }
      }
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
    revert_changes() {
      if (!confirm('Are you sure you want to revert to the last version? This cannot be undone.')) {
        return
      }
      const that = this
      const last_version = that.appStateStore.selected_writing_task.previous_versions?.pop()
      if (!last_version) {
        return
      }
      that.appStateStore.selected_writing_task.text = last_version.text
      that.appStateStore.selected_writing_task.additional_results = last_version.additional_results
      const body = {
        task_id: this.appStateStore.selected_writing_task_id,
      }
      httpClient.post(`/org/data_map/revert_writing_task`, body)
      .then(function (response) {
        // pass
      })
      .catch(function (error) {
        console.error(error)
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
  <div class="mt-2 ml-5 mr-6 pl-2 flex flex-col gap-2">

    <h2 class="text-lg font-bold font-serif">Summary: How can Mxenes be used?</h2>
    <p class="text-sm text-gray-700">
      MXenes have been investigated experimentally in lithium-ion batteries (LIBs) (e.g. V2CTx ,[25] Nb2CTx ,[25] Ti2CTx ,[78] and Ti3C2Tx[42]). V2CTx has demonstrated the highest reversible charge storage capacity among MXenes in multi-layer form (280 mAhg−1 at 1C rate and 125 mAhg−1 at 10C rate). Multi-layer Nb2CTx showed a stable, reversible capacity of 170 mAhg−1 at 1C rate and 110 mAhg−1 at a 10C rate.
    </p>
    <p class="text-sm text-gray-700">
      Although Ti3C2Tx shows the lowest capacity among the four MXenes in multi-layer form, it can be delaminated via sonication of the multi-layer powder. By virtue of higher electrochemically active and accessible surface area, delaminated Ti3C2Tx paper demonstrates a reversible capacity of 410 mAhg−1 at 1C and 110 mAhg−1 at 36C rate.
    </p>

    <h2 class="mt-5 text-lg font-bold font-serif">Potential Research Areas</h2>
    <p class="text-sm text-gray-700">
      MXenes have been investigated experimentally in lithium-ion batteries (LIBs) (e.g. V2CTx ,[25] Nb2CTx ,[25] Ti2CTx ,[78] and Ti3C2Tx[42]). V2CTx has demonstrated the highest reversible charge storage capacity among MXenes in multi-layer form (280 mAhg−1 at 1C rate and 125 mAhg−1 at 10C rate). Multi-layer Nb2CTx showed a stable, reversible capacity of 170 mAhg−1 at 1C rate and 110 mAhg−1 at a 10C rate.
    </p>

    <div class="flex flex-row gap-2 items-center justify-center" v-if="false">
      <Dropdown
        v-model="appState.selected_writing_task_id"
        :options="writing_task_ids"
        optionLabel="name"
        optionValue="id"
        placeholder="Select Writing Task..."
        class="flex-1 h-full text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      <InputGroup class="flex-1">
        <InputText placeholder="New Writing Task" v-model="new_writing_task_name" />
        <Button label="Add" @click="add_writing_task(new_writing_task_name)"></Button>
      </InputGroup>
    </div>

    <div v-if="appState.selected_writing_task" class="flex-1 flex flex-col gap-2 overflow-y-auto">

      <div class="flex flex-row items-center">
        <span class="text-sm">Prompt:</span>
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
        <button @click="update_writing_task()" class="px-2 py-1 rounded text-sm bg-gray-100 hover:bg-blue-100/50">Save Changes</button>
        <button @click="execute_writing_task()" class="px-2 py-1 rounded text-sm bg-green-100 hover:bg-blue-100/50">(Re-)generate</button>
        <div class="flex-1"></div>
        <button v-if="appState.selected_writing_task.previous_versions?.length > 0"
          @click="revert_changes()"
          v-tooltip.left="{'value': 'Go back to last version', showDelay: 500}"
          class="h-6 w-6 rounded bg-gray-100 hover:text-blue-500">
          <BackwardIcon class="m-1"></BackwardIcon>
        </button>
      </div>
      <p v-if="appState.selected_writing_task.is_processing" class="text-sm text-gray-500">Processing...</p>

      <Message v-if="!appState.selected_writing_task.use_all_items" severity="warn">Using selected items is not yet implemented</Message>

      <div class="relative flex-1 mt-2 flex flex-col overflow-hidden">
        <textarea v-if="edit_mode"
          v-model="appState.selected_writing_task.text"
          class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 text-sm shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"/>
        <div v-if="!edit_mode" class="w-full h-full">
          <div v-html="marked.parse(appState.selected_writing_task.text)"
            class="w-full h-full text-sm use-default-html-styles use-default-html-styles-large overflow-y-auto"></div>
        </div>
        <button @click="edit_mode = !edit_mode"
          v-tooltip.left="{'value': 'Edit', showDelay: 500}"
          class="absolute top-0 right-0 h-6 w-6 rounded bg-gray-100 hover:text-blue-500"
          :class="{'text-gray-500': !edit_mode, 'text-blue-500': edit_mode}">
          <PencilIcon class="m-1"></PencilIcon>
        </button>
      </div>

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

      <textarea v-model="references" readonly
        class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"/>

    </div>
  </div>

</template>

<style>

.use-default-html-styles-large p {
  margin: 0 0 1em 0;
}

.use-default-html-styles-large ul {
  margin: 0 0 1em 0;
}

.use-default-html-styles-large ol {
  margin: 0 0 1em 0;
}
</style>

<style scoped>
</style>
