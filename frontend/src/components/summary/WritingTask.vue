<script setup>

import {
  ArrowPathIcon,
  TrashIcon,
  AdjustmentsHorizontalIcon,
  PencilIcon,
  BackwardIcon,
  CheckIcon,
 } from "@heroicons/vue/24/outline"
import {marked} from "marked";

import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import ProgressSpinner from "primevue/progressspinner";
import Dialog from "primevue/dialog";
import MultiSelect from "primevue/multiselect";
import OverlayPanel from "primevue/overlaypanel";
import Skeleton from "primevue/skeleton";

import BorderlessButton from "../widgets/BorderlessButton.vue";
import ReferenceHoverInfo from "../collections/ReferenceHoverInfo.vue";

import { httpClient, djangoClient } from "../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()

window.reference_clicked = function (dataset_id, item_id, event) {
  appState.show_document_details([dataset_id, item_id])
}

window.reference_mouse_enter = function (dataset_id, item_id, event) {
  window.eventBus.emit("reference_mouse_enter", {dataset_id, item_id, event})
}

window.reference_mouse_leave = function (dataset_id, item_id, event) {
  window.eventBus.emit("reference_mouse_leave", {dataset_id, item_id, event})
}

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["writing_task_id"],
  emits: ["delete"],
  data() {
    return {
      writing_task: null,
      edit_mode: false,

      show_settings_dialog: false,
      selected_citation_dataset_id: null,
      selected_citation_item_id: null,
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
    text_with_links() {
      if (!this.writing_task || !this.writing_task.text) {
        return 'No text yet'
      }
      let text = this.writing_task.text;
      const regex = /\[([0-9]+),\s([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\]/g;
      let match;
      let reference_order = []
      while ((match = regex.exec(text)) !== null) {
        try {
          const dataset_id = match[1]
          const item_id = match[2]
          const item = this.writing_task.additional_results.reference_metadata[dataset_id][item_id]
          let i = reference_order.length + 1
          if (reference_order.includes(item_id)) {
            i = reference_order.indexOf(item_id) + 1
          } else {
            reference_order.push(item_id)
          }
          const rendering = this.appStateStore.datasets[dataset_id].schema.result_list_rendering
          const title = rendering.title(item)
          const replacement = `<span \
            onmouseenter="reference_mouse_enter('${dataset_id}', '${item_id}', event); return false;" \
            onmouseleave="reference_mouse_leave('${dataset_id}', '${item_id}', event); return false;" \
            onclick="reference_clicked('${dataset_id}', '${item_id}', event); return false;" \
            class="text-sky-700 cursor-pointer">[${i}]</span>`;
          text = text.replace(match[0], replacement);
        } catch (error) {
          console.error(error)
          text = text.replace(match[0], `[${i}]`);
        }
      }
      return marked.parse(text)
    },
  },
  watch: {
    edit_mode(new_val, old_val) {
      if (!new_val) {
        this.update_writing_task()
      }
    },
  },
  mounted() {
    this.get_writing_task(() => {
      if (this.writing_task.name !== 'Summary+') return
      this.writing_task.name = 'Summary'
      this.writing_task.module = 'groq_llama_3_70b'
      this.writing_task.source_fields = ['_full_text_snippets', '_descriptive_text_fields']
      this.writing_task.use_all_items = true
      this.writing_task.prompt = "Summarize the items in three short bullet points. Use markdown syntax."
      this.update_writing_task(() => {
        this.execute_writing_task()
      })
    })
    this.eventBus.on("agent_stopped", () => {
      this.get_writing_task()
    })
    this.eventBus.on("reference_mouse_enter", ({dataset_id, item_id, event}) => {
      // TODO: this is not unregistered when the component is destroyed
      if (!dataset_id || !item_id || !event) {
        return
      }
      this.selected_citation_dataset_id = dataset_id
      this.selected_citation_item_id = item_id
      this.$refs.citation_tooltip?.toggle(event)
    })
    this.eventBus.on("reference_mouse_leave", ({dataset_id, item_id, event}) => {
      this.$refs.citation_tooltip?.hide()
    })
  },
  methods: {
    get_writing_task(on_success=null) {
      if (!this.writing_task_id) {
        return
      }
      const that = this
      const body = {
        task_id: this.writing_task_id,
      }
      httpClient.post(`/org/data_map/get_writing_task_by_id`, body)
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
      const body = {
        task_id: this.writing_task_id,
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
    execute_writing_task() {
      const that = this
      this.update_writing_task(() => {
        const body = {
          task_id: this.writing_task_id,
        }
        httpClient.post(`/org/data_map/execute_writing_task`, body)
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
      if (!confirm('Are you sure you want to revert to the last version? This cannot be undone.')) {
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
  <div class="flex flex-col gap-3" v-if="writing_task">

    <div class="flex flex-row gap-3">
      <h2 class="text-lg font-bold font-serif">
        {{ writing_task.name || "New Writing Task" }}
      </h2>
      <div class="flex-1"></div>
      <BorderlessButton v-if="!writing_task.is_processing"
        @click="execute_writing_task" v-tooltip.bottom="{ value: 'Re-generate this writing task' }"
        hover_color="hover:text-green-500" :default_padding="false" class="h-6 w-6">
        <ArrowPathIcon class="h-4 w-4"></ArrowPathIcon>
      </BorderlessButton>
      <ProgressSpinner v-if="writing_task.is_processing" class="h-6 w-6" strokeWidth="8" style="color: #4CAF50" />
      <BorderlessButton @click="show_settings_dialog = true"
        v-tooltip.bottom="{ value: 'Configure this writing task' }"
        :default_padding="false" class="h-6 w-6">
        <AdjustmentsHorizontalIcon class="h-4 w-4"></AdjustmentsHorizontalIcon>
      </BorderlessButton>
      <BorderlessButton @click="$emit('delete')"
        v-tooltip.bottom="{ value: 'Delete writing task' }"
        hover_color="hover:text-red-500" :default_padding="false" class="h-6 w-6">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </BorderlessButton>
    </div>

    <div class="relative flex-1 mt-2 flex flex-col gap-1" id="writing_task_body">
      <Skeleton v-if="writing_task.is_processing" height="1rem" width="80%" class="flex-none" />
      <Skeleton v-if="writing_task.is_processing" height="1rem" class="flex-none" />

      <textarea v-if="edit_mode && !writing_task.is_processing"
        v-model="writing_task.text"
        class="w-full h-[300px] rounded-md border-0 py-1.5 text-gray-900 text-sm shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"/>
      <div v-if="!edit_mode && !writing_task.is_processing" class="w-full h-full">
        <div v-html="text_with_links"
          class="w-full h-full text-sm use-default-html-styles use-default-html-styles-large overflow-y-auto"></div>
      </div>
      <button @click="edit_mode = !edit_mode" v-if="!writing_task.is_processing"
        v-tooltip.left="{'value': edit_mode ? 'Save' : 'Edit', showDelay: 500}"
        class="absolute bottom-0 right-0 h-6 w-6 rounded bg-gray-100 hover:text-blue-500 show-when-parent-is-hovered transition-opacity"
        :class="{'text-gray-500': !edit_mode, 'text-blue-500': edit_mode}">
        <PencilIcon class="m-1" v-if="!edit_mode"></PencilIcon>
        <CheckIcon class="m-1" v-else></CheckIcon>
      </button>
    </div>

    <OverlayPanel ref="citation_tooltip">
      <ReferenceHoverInfo
        class="w-[500px]"
        :dataset_id="selected_citation_dataset_id"
        :item_id="selected_citation_item_id">
      </ReferenceHoverInfo>
    </OverlayPanel>

    <Dialog v-model:visible="show_settings_dialog" modal header="Writing Task">

      <div class="flex flex-col gap-5">

        <input v-model="writing_task.name" placeholder="Name"
          class="" />

        <textarea v-model="writing_task.prompt" placeholder="prompt"
          class="rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />

          <div class="flex flex-row gap-2 items-center">
        <div class="flex-1 min-w-0">
          <MultiSelect v-model="writing_task.source_fields"
            :options="available_source_fields"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Sources..."
            :maxSelectedLabels="0"
            selectedItemsLabel="{0} Source(s)"
            class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
        <div class="flex-1 min-w-0">
          <Dropdown v-model="writing_task.module"
            :options="appState.available_ai_modules"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Select Module.."
            class="w-full h-full text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
        </div>
      </div>

      <button v-if="writing_task.previous_versions?.length > 0"
        @click="revert_changes()"
        v-tooltip.left="{'value': 'Go back to last version', showDelay: 500}"
        class="h-6 w-6 rounded bg-gray-100 hover:text-blue-500">
        <BackwardIcon class="m-1"></BackwardIcon>
      </button>

      <button @click="update_writing_task(); show_settings_dialog = false" class="px-2 py-1 rounded text-sm bg-gray-100 hover:bg-blue-100/50">
        Save Changes
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
