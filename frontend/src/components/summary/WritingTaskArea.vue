<script setup>
import {

} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import WritingTask from "./WritingTask.vue";
import BorderButton from "../widgets/BorderButton.vue";

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
      quick_question_text: '',
      item_selection_options: [
        {label: 'All Items', value: true},
        {label: 'Selected Items', value: false},
      ],
      edit_mode: false,
      show_used_prompt: false,

      templates: [
        {
          intent: 'Summarize the items',
          name: 'Summary',
          options: {
            prompt: 'Summarize the main points of the items in this collection.',
            source_fields: ['_descriptive_text_fields'],
            module: 'groq_llama_3_70b',
            use_all_items: true,
          }
        },
        {
          intent: 'Key Challenges',
          name: 'Challenges',
          options: {
            prompt: 'Summarize the key challenges mentioned in the items in this collection.',
            source_fields: ['_descriptive_text_fields'],
            module: 'groq_llama_3_70b',
            use_all_items: true,
          }
        },
        {
          intent: 'Possible Research Questions',
          name: 'Research Questions',
          options: {
            prompt: 'What are some possible research questions that come up when looking at the items in this collection? Use bullet points in markdown syntax.',
            source_fields: ['_descriptive_text_fields'],
            module: 'groq_llama_3_70b',
            use_all_items: true,
          }
        },
      ]
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
    add_writing_task(name, options = null, run_now = false) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        name: name,
        options: options,
        run_now: run_now,
      }
      httpClient.post(`/org/data_map/add_writing_task`, body)
      .then(function (response) {
        const task = response.data
        that.writing_task_ids.push(task)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    create_from_template(template) {
      this.add_writing_task(template.name, template.options, true)
    },
    quick_question(question) {
      const options = {
        prompt: question,
        source_fields: ['_descriptive_text_fields', '_all_columns'],
        module: 'openai_gpt_4_o',
        use_all_items: true,
      }
      this.add_writing_task(question, options, true)
      this.quick_question_text = ''
    },
    delete_writing_task(writing_task_id) {
      const that = this
      const body = {
        task_id: writing_task_id,
      }
      httpClient.post(`/org/data_map/delete_writing_task`, body)
      .then(function (response) {
        that.writing_task_ids = that.writing_task_ids.filter((task) => task.id !== writing_task_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div class="pt-7 pb-10 pl-10 pr-10 flex flex-col gap-5">

    <WritingTask v-for="task in writing_task_ids" :key="task.id"
      :writing_task_id="task.id"
      @delete="delete_writing_task(task.id)"
    />

    <div class="flex-1"></div>

    <div class="flex flex-col gap-2">
      <span class="text-xs text-gray-400 text-center">
        Ask questions that can be answered using the items in this collection.
      </span>

      <div class="flex flex-row gap-2">
        <input v-model="quick_question_text" placeholder="Quick Question"
          @keyup.enter="quick_question(quick_question_text)"
          class="flex-1 px-2 py-1 rounded text-sm text-gray-800 border border-gray-200" />
        <BorderButton @click="quick_question(quick_question_text)"
          class="">
          Ask
        </BorderButton>
      </div>


      <div class="flex flex-row gap-3">
        <BorderButton @click="add_writing_task('New Writing Task')"
          class="flex-1 px-2 py-1">
          Create custom writing task
        </BorderButton>
      </div>
    </div>

    <div class="flex flex-col gap-2 items-start" v-if="writing_task_ids.length === 0">
      <span class="text-sm text-gray-500">
        Ideas:
      </span>
      <button v-for="template in templates" :key="template.intent"
        @click="create_from_template(template)"
        class="flex-1 px-3 py-1 rounded text-sm text-gray-500 bg-gray-100 hover:text-blue-500">
        {{ template.intent }}
      </button>
    </div>

    <!-- <div class="flex flex-row gap-2 items-center justify-center" v-if="false">
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

    </div> -->
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
