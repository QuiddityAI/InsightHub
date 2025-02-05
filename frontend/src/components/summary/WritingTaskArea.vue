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

      templates: [
        {
          intent: 'Summarize the items',
          name: 'Summary',
          options: {
            expression: 'Summarize the main points of the items in this collection.',
            source_fields: ['_descriptive_text_fields'],
            model: 'Mistral_Mistral_Large',
            use_all_items: true,
          }
        },
        {
          intent: 'Key Challenges',
          name: 'Challenges',
          options: {
            expression: 'Summarize the key challenges mentioned in the items in this collection.',
            source_fields: ['_descriptive_text_fields'],
            model: 'Mistral_Mistral_Large',
            use_all_items: true,
          }
        },
        {
          intent: 'Possible Research Questions',
          name: 'Research Questions',
          options: {
            expression: 'What are some possible research questions that come up when looking at the items in this collection? Use bullet points in markdown syntax.',
            source_fields: ['_descriptive_text_fields'],
            model: 'Mistral_Mistral_Large',
            use_all_items: true,
          }
        },
      ]
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
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
    add_writing_task(name, options = {}, run_now = false) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        name: name,
        options: options,
        run_now: run_now,
      }
      if (this.appStateStore.user.preferences.default_large_llm) {
        body.options.model = this.appStateStore.user.preferences.default_large_llm
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
        expression: question,
        source_fields: ['_descriptive_text_fields', '_all_columns'],
        model: 'Mistral_Mistral_Large',
        use_all_items: true,
      }
      let name_ellipsis = question.slice(0, 100)
      if (name_ellipsis.length < question.length) {
        name_ellipsis += '...'
      }
      this.add_writing_task(name_ellipsis, options, true)
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
    insertNewline(event) {
      const textarea = event.target;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      this.quick_question_text = this.quick_question_text.substring(0, start) + '\n' + this.quick_question_text.substring(end);
      this.$nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1;
      });
    }
  },
}
</script>

<template>
  <div class="pl-14 pr-16">

    <div class="h-full flex flex-col gap-5 max-w-[600px] min-w-0 mx-auto pt-10">

      <WritingTask v-for="task in writing_task_ids" :key="task.id"
        :writing_task_id="task.id"
        @delete="delete_writing_task(task.id)"
      />

      <div class="flex-1"></div>

      <div class="flex flex-col gap-2 items-start mb-10" v-if="writing_task_ids.length === 0">
        <span class="text-sm text-gray-500">
          {{ $t('WritingTaskArea.ideas') }}
        </span>
        <button v-for="template in templates" :key="template.intent"
          @click="create_from_template(template)"
          class="flex-1 px-3 py-1 rounded text-sm text-gray-500 bg-gray-100 hover:text-blue-500">
          {{ template.intent }}
        </button>
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-400 text-center">
          {{ $t('WritingTaskArea.hint-only-ask-about-existing-items') }}
        </span>

        <div class="flex flex-row gap-2">
          <textarea v-model="quick_question_text" :placeholder="$t('WritingTaskArea.quick-question-placeholder')"
            @keyup.enter="!$event.shiftKey && quick_question(quick_question_text)"
            @keydown.enter.prevent="!$event.shiftKey"
            @keydown.shift.enter.stop
            @keydown.shift.enter="insertNewline"
            class="flex-1 px-2 py-1 rounded text-sm text-gray-800 border border-gray-200 h-8" />
          <BorderButton @click="quick_question(quick_question_text)"
            class="">
            {{ $t('WritingTaskArea.question-submit-button') }}
          </BorderButton>
        </div>


        <div class="flex flex-row gap-3">
          <BorderButton @click="add_writing_task($t('WritingTaskArea.new-writing-task-name'))"
            class="flex-1 px-2 py-1">
            {{ $t('WritingTaskArea.create-custom-writing-task') }}
          </BorderButton>
        </div>
      </div>

      <div class="flex-none h-5 w-full"></div>

    </div>

  </div>

</template>

<style scoped>
</style>
