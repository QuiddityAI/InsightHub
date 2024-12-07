<script setup>

import { useToast } from 'primevue/usetoast';

import WritingTask from "./WritingTask.vue";
import BorderButton from "../widgets/BorderButton.vue";
import BorderlessButton from "../widgets/BorderlessButton.vue";

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
            module: 'Mistral_Mistral_Large',
            use_all_items: true,
          }
        },
        {
          intent: 'Key Challenges',
          name: 'Challenges',
          options: {
            prompt: 'Summarize the key challenges mentioned in the items in this collection.',
            source_fields: ['_descriptive_text_fields'],
            module: 'Mistral_Mistral_Large',
            use_all_items: true,
          }
        },
        {
          intent: 'Possible Research Questions',
          name: 'Research Questions',
          options: {
            prompt: 'What are some possible research questions that come up when looking at the items in this collection? Use bullet points in markdown syntax.',
            source_fields: ['_descriptive_text_fields'],
            module: 'Mistral_Mistral_Large',
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
      httpClient.post(`/api/v1/write/get_writing_tasks`, body)
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
      httpClient.post(`/api/v1/write/add_writing_task`, body)
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
      if (!question) {
        return
      }
      const options = {
        prompt: question,
        source_fields: ['_descriptive_text_fields', '_all_columns'],
        module: 'Mistral_Mistral_Large',
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
      httpClient.post(`/api/v1/write/delete_writing_task`, body)
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
  <div class="flex flex-col items-center pt-10 pb-10 pl-14 pr-16 relative">

    <div class="flex-1 flex flex-col gap-5 max-w-[700px]">

      <WritingTask v-for="task in writing_task_ids" :key="task.id"
        :writing_task_id="task.id"
        @delete="delete_writing_task(task.id)"
      />

      <div class="flex-1"></div>

      <div class="flex flex-col gap-2 items-start mb-10" v-if="writing_task_ids.length === 0">
        <span class="text-sm text-gray-500">
          Ideas:
        </span>
        <button v-for="template in templates" :key="template.intent"
          @click="create_from_template(template)"
          class="flex-1 px-3 py-1 rounded text-sm text-gray-500 bg-gray-100 hover:text-blue-500">
          {{ template.intent }}
        </button>
      </div>

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
