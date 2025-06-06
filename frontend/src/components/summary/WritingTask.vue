<script setup>

import {
  ArrowPathIcon,
  TrashIcon,
  AdjustmentsHorizontalIcon,
  BackwardIcon,
 } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import ProgressSpinner from "primevue/progressspinner";
import Dialog from "primevue/dialog";
import MultiSelect from "primevue/multiselect";
import Skeleton from "primevue/skeleton";
import Checkbox from "primevue/checkbox";

import BorderlessButton from "../widgets/BorderlessButton.vue";
import TipTapEditor from "../text_editor/TipTapEditor.vue";
import LlmSelect from "../widgets/LlmSelect.vue";

import { debounce, META_SOURCE_FIELDS } from "../../utils/utils"

import { httpClient } from "../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["writing_task_id"],
  emits: ["delete"],
  data() {
    return {
      writing_task: null,
      show_settings_dialog: false,
      show_used_prompt: false,
      use_default_prompt: true,
      update_writing_task_debounce: debounce((event) => {
          this.update_writing_task()
        }, 500),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
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
      for (const column of this.collectionStore.collection.columns) {
        available_fields[column.identifier] = {
          identifier: '_column__' + column.identifier,
          name: this.$t('general.column') + ': ' + column.name,
        }
      }
      available_fields[META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS] = {
        identifier: META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
        name: this.$t('general.descriptive-text-fields'),
      }
      available_fields[META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS] = {
        identifier: META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
        name: this.$t('general.full-text-excerpts'),
      }
      available_fields[META_SOURCE_FIELDS.ALL_COLUMNS] = {
        identifier: META_SOURCE_FIELDS.ALL_COLUMNS,
        name: this.$t('WritingTask.all-column-content'),
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
  },
  watch: {
    "writing_task.prompt_template" (new_val, old_val) {
      if (new_val === old_val) {
        return
      }
      this.use_default_prompt = !new_val
    },
    "use_default_prompt" (new_val, old_val) {
      if (new_val === old_val) {
        return
      }
      if (new_val) {
        this.writing_task.prompt_template = ""
      }
    },
  },
  mounted() {
    this.get_writing_task(() => {
      this.use_default_prompt = !this.writing_task.prompt_template
    })
    this.eventBus.on("agent_stopped", this.on_agent_stopped)
  },
  unmounted() {
    this.eventBus.off("agent_stopped", this.on_agent_stopped)
  },
  methods: {
    on_agent_stopped() {
      this.get_writing_task()
    },
    get_writing_task(on_success=null) {
      if (!this.writing_task_id) {
        return
      }
      const that = this
      const body = {
        task_id: this.writing_task_id,
      }
      httpClient.post(`/api/v1/write/get_writing_task_by_id`, body)
      .then(function (response) {
        that.writing_task = response.data
        if (that.writing_task.is_processing) {
          setTimeout(() => {
            that.get_writing_task()
          }, 1000)
        }
        if (on_success) {
          on_success()
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    update_writing_task(on_success=null) {
      const that = this
      const task = this.writing_task
      // remove trailing newlines from task.name:
      task.name = task.name.replace(/\n+$/, '')
      const body = {
        task_id: this.writing_task_id,
        name: task.name,
        source_fields: task.source_fields,
        selected_item_ids: task.selected_item_ids,
        model: task.model,
        parameters: task.parameters,
        expression: task.expression,
        prompt_template: task.prompt_template,
        text: task.text,
      }
      httpClient.post(`/api/v1/write/update_writing_task`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    execute_writing_task() {
      const that = this
      this.update_writing_task(() => {
        const body = {
          task_id: this.writing_task_id,
        }
        httpClient.post(`/api/v1/write/execute_writing_task`, body)
        .then(function (response) {
          that.writing_task.is_processing = true
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
      if (!confirm(this.$t('WritingTask.revert-changes-alert'))) {
        return
      }
      const that = this
      const last_version = that.writing_task.previous_versions?.pop()
      if (!last_version) {
        return
      }
      that.writing_task.text = last_version.text
      that.writing_task.additional_results = last_version.additional_results
      const body = {
        task_id: this.writing_task_id,
      }
      httpClient.post(`/api/v1/write/revert_writing_task`, body)
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
  <div class="flex flex-col gap-3" v-if="writing_task">

    <div class="relative flex flex-row gap-3">
      <h2 class="flex-1 peer text-lg font-bold font-['Lexend']"
        contenteditable @blur="writing_task.name = $event.target.innerText; update_writing_task_debounce()"
        @keydown.enter="$event.target.blur()" @keydown.esc="$event.target.innerText = writing_task.name; $event.target.blur()"
        spellcheck="false">
        {{ writing_task.name }}
      </h2>
      <h2 class="absolute top-0 text-lg font-bold font-['Lexend'] text-gray-500 peer-focus:hidden pointer-events-none">
        <span v-if="!writing_task.name">{{ $t('WritingTask.writing-task-name-placeholder') }}</span>
      </h2>
      <BorderlessButton v-if="appState.user.is_staff"
        @click="show_used_prompt = true" v-tooltip.bottom="{ value: $t('WritingTask.show-the-used-prompt') }"
        :default_padding="false" class="h-6 w-6">
        P
        <Dialog v-model:visible="show_used_prompt" modal :header="$t('WritingTask.used-prompt-dialog-header')">
          <div class="overflow-y-auto max-h-[400px]"
            v-html="convert_to_html(writing_task.additional_results.used_prompt)" />
        </Dialog>
      </BorderlessButton>
      <BorderlessButton v-if="!writing_task.is_processing"
        @click="execute_writing_task" v-tooltip.bottom="{ value: $t('WritingTask.regenerate-this-writing-task') }"
        hover_color="hover:text-green-500" :default_padding="false" class="h-6 w-6">
        <ArrowPathIcon class="h-4 w-4"></ArrowPathIcon>
      </BorderlessButton>
      <ProgressSpinner v-if="writing_task.is_processing" class="h-6 w-6" strokeWidth="8" style="color: #4CAF50" />
      <BorderlessButton @click="show_settings_dialog = true"
        v-tooltip.bottom="{ value: $t('WritingTask.configure-this-writing-task') }"
        :default_padding="false" class="h-6 w-6">
        <AdjustmentsHorizontalIcon class="h-4 w-4"></AdjustmentsHorizontalIcon>
      </BorderlessButton>
      <BorderlessButton @click="$emit('delete')"
        v-tooltip.bottom="{ value: $t('WritingTask.delete-writing-task') }"
        hover_color="hover:text-red-500" :default_padding="false" class="h-6 w-6">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </BorderlessButton>
    </div>

    <div class="relative flex-1 mt-2 flex flex-col gap-1" id="writing_task_body">
      <Skeleton v-if="writing_task.is_processing" height="1rem" width="80%" class="flex-none" />
      <Skeleton v-if="writing_task.is_processing" height="1rem" class="flex-none" />

      <div v-if="!writing_task.is_processing" class="w-full h-full">
        <TipTapEditor v-model="writing_task.text" @change="update_writing_task_debounce"
          :reference_order="writing_task.additional_results.references"/>
      </div>
    </div>

    <Dialog v-model:visible="show_settings_dialog" modal :header="$t('WritingTask.writing-task-dialog-name')">

      <div class="flex flex-col gap-5">

        <textarea v-model="writing_task.expression" :placeholder="$t('WritingTask.expression-placeholder')"
          class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />

        <div class="flex flex-row gap-1">
          <Checkbox inputId="writing_task_use_default_prompt" v-model="use_default_prompt"
            :binary="true" class="text-sm text-gray-500" />
          <label for="writing_task_use_default_prompt" class="text-sm text-gray-500">
            {{ $t('WritingTask.use-default-system-prompt') }}
          </label>
         </div>

        <textarea v-if="!use_default_prompt"
          v-model="writing_task.prompt_template" :placeholder="$t('WritingTask.prompt-template-placeholder', ['{{ context }}', '{{ expression }}'])"
          class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />

          <div class="flex flex-row gap-2 items-center">
        <div class="flex-1 min-w-0">
          <MultiSelect v-model="writing_task.source_fields"
            :options="available_source_fields"
            optionLabel="name"
            optionValue="identifier"
            :placeholder="$t('WritingTask.select-sources-placeholder')"
            :maxSelectedLabels="0"
            :selectedItemsLabel="`{0} ` + $t('WritingTask.source-select-label')"
            class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
        <div class="flex-1 min-w-0">
          <LlmSelect v-model="writing_task.model"
            :tooltip="$t('WritingTask.model-select-tooltip')" />
        </div>
      </div>

      <button v-if="writing_task.previous_versions?.length > 0"
        @click="revert_changes()"
        v-tooltip.left="{'value': $t('WritingTask.revert-changes-tooltip'), showDelay: 500}"
        class="h-6 w-6 rounded bg-gray-100 hover:text-blue-500">
        <BackwardIcon class="m-1"></BackwardIcon>
      </button>

      <button @click="update_writing_task(); show_settings_dialog = false" class="px-2 py-1 rounded text-sm bg-gray-100 hover:bg-blue-100/50">
        {{ $t('WritingTask.save-changes') }}
      </button>

      </div>

    </Dialog>

  </div>
</template>

<style scoped>
.show-when-parent-is-hovered {
  opacity: 0;
}

#writing_task_body:hover > .show-when-parent-is-hovered{
  opacity: 1;
}
</style>
