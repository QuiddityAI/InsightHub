<script setup>
import { httpClient } from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import OverlayPanel from 'primevue/overlaypanel';

import ChatList from "../chats/ChatList.vue"
import CollectionTableView from "./CollectionTableView.vue"
import ExportCollectionArea from "./ExportCollectionArea.vue";
import ExportTableArea from "./ExportTableArea.vue";
import { FieldType } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["collection_id", "class_name"],
  emits: ["close"],
  data() {
    return {
      selected_tab: "positives",
      collection: useAppStateStore().collections.find((collection) => collection.id === this.collection_id),
      target_vector_ds_and_field: null,
      trained_classifier: null,
      is_retraining: false,
      retraining_progress: 0.0,
      show_retrain_success_label: false,
      table_visible: false,
      show_export_dialog: false,
    }
  },
  watch: {
    target_vector_ds_and_field() {
      this.get_trained_classifier()
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
    last_retraining_human_readable() {
      return new Date(this.trained_classifier?.last_retrained_at).toLocaleString()
    },
    embedding_space_identifier() {
      if (!this.target_vector_ds_and_field) {
        return null
      }
      const dataset = this.appStateStore.datasets[this.target_vector_ds_and_field[0]]
      return dataset.schema.object_fields[this.target_vector_ds_and_field[1]].actual_embedding_space.identifier
    },
    class_details() {
      return this.collection.actual_classes.find((collection_class) => collection_class.name === this.class_name)
    }
  },
  mounted() {
    this.target_vector_ds_and_field = this.appStateStore.available_vector_fields.find((ds_and_field) => ds_and_field[1] === this.appStateStore.settings.vectorize.map_vector_field)
    if (!this.target_vector_ds_and_field) {
      this.target_vector_ds_and_field = this.appStateStore.available_vector_fields[0]
    }
    this.get_trained_classifier()
    this.get_retraining_status()
  },
  methods: {
    delete_collection() {
      if (!confirm("Are you sure you want to delete this collection?")) {
        return
      }
      const that = this
      const delete_collection_body = {
        collection_id: this.collection_id,
      }
      httpClient
        .post("/org/data_map/delete_collection", delete_collection_body)
        .then(function (response) {
          const index = that.appStateStore.collections.findIndex((collection) => collection.id === that.collection_id)
          that.appStateStore.collections.splice(index, 1)
        })
      this.$emit("close")
    },
    get_trained_classifier() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        embedding_space_identifier: this.embedding_space_identifier,
        include_vector: false,
      }
      httpClient.post(`/org/data_map/get_trained_classifier`, body)
      .then(function (response) {
        that.trained_classifier = response.data
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    retrain() {
      const that = this
      if (this.is_retraining) {
        return
      }
      this.is_retraining = true
      this.retraining_progress = 0.0
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        embedding_space_identifier: this.embedding_space_identifier,
        deep_train: false,
      }
      httpClient.post(`/data_backend/classifier/retrain`, body)
      .then(function (response) {
        that.get_retraining_status()
      })
      .catch(function (error) {
        that.is_retraining = false
        that.retraining_progress = 0.0
        console.error(error)
      })
    },
    get_retraining_status() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        embedding_space_identifier: this.embedding_space_identifier,
      }
      httpClient.post(`/data_backend/classifier/retraining_status`, body)
      .then(function (response) {
        const status = response.data
        if (!status) {
          that.is_retraining = false
          that.retraining_progress = 0.0
        } else if (status.status === "done") {
          that.is_retraining = false
          that.retraining_progress = 0.0
          that.last_retraining = Math.floor(Date.now() / 1000)
          that.show_retrain_success_label = true
          setTimeout(() => {
            that.show_retrain_success_label = false
          }, 2000)
        } else if (status.status === "error") {
          that.is_retraining = false
          that.retraining_progress = 0.0
        } else {
          that.retraining_progress = status.progress
          setTimeout(that.get_retraining_status, 300)
        }
      })
      .catch(function (error) {
        that.is_retraining = false
        that.retraining_progress = 0.0
        console.error(error)
      })
    },
    show_map() {
      this.appStateStore.reset_search_box()
      this.appStateStore.settings.search.all_field_query = this.collection.search_intent
      this.appStateStore.request_search_results()
    },
    show_table() {
      this.table_visible = true
      if (!this.$refs.table_dialog.maximized) {
        this.$refs.table_dialog.maximize()
      }
    }
  },
}
</script>

<template>
  <div class="flex flex-col overflow-hidden pt-1 pl-1">
    <div class="flex-none flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="text-md font-bold text-black">{{ collection.name }}</span>
      <span class="text-medium text-gray-500">
        {{ class_name === '_default' ? '' : ': ' + class_name }}
      </span>

      <div class="flex-1"></div>

      <!-- <div class="w-40 h-6">
        <select
          v-model="target_vector_ds_and_field"
          class="w-full py-0 rounded border-transparent text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
          <option v-for="item in appState.available_vector_fields" :value="item" selected>
            {{ appState.datasets[item[0]]?.name }}: {{ item[1] }}
          </option>
        </select>
      </div>

      <button
        class="relative h-6 items-center justify-center rounded-md text-gray-400 bg-gray-100"
        @click="retrain"
        :disabled="is_retraining"
        :title="`Last retraining: ${last_retraining_human_readable}, embedding space ${embedding_space_identifier}`">
        <div class="absolute h-full bg-blue-500/20 rounded-md" :style="{ width: `${retraining_progress * 100}%` }"></div>
        <span class="mx-2 hover:text-blue-500">{{ is_retraining ? "Retraining..." : (show_retrain_success_label ? "Retrained ✓": "Retrain") }}</span>
      </button> -->

      <button @click="show_export_dialog = true"
        class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2 text-gray-500 font-semibold text-sm">
          Export Items Only
      </button>

      <button @click="event => {$refs.export_dialog.toggle(event)}"
        class="py-1 px-2 rounded-md bg-gray-100 text-gray-500 text-sm font-semibold hover:bg-blue-100/50">
        Export Table
      </button>
      <OverlayPanel ref="export_dialog">
        <ExportTableArea :collection_id="collection_id" :class_name="class_name">
        </ExportTableArea>
      </OverlayPanel>

      <Dialog v-model:visible="show_export_dialog" modal header="Export">
        <ExportCollectionArea :collection_id="collection_id" :class_name="class_name">
        </ExportCollectionArea>
      </Dialog>

      <button
        @click="delete_collection"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <CollectionTableView
      class="flex-1 overflow-hidden mt-3"
      :collection_id="collection_id"
      :class_name="class_name"
      :is_positive="true">
    </CollectionTableView>

    <!-- <ChatList
      v-if="selected_tab === 'chat'"
      :collection_id="collection_id"
      :class_name="class_name">
    </ChatList> -->

  </div>
</template>
