<script setup>
import { httpClient } from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import Button from 'primevue/button';

import CollectionItemList from "./CollectionItemList.vue"
import ChatList from "../chats/ChatList.vue"
import CollectionTableView from "./CollectionTableView.vue"
import ExportCollectionArea from "./ExportCollectionArea.vue";
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
    embedding_space_id() {
      if (!this.target_vector_ds_and_field) {
        return null
      }
      const dataset = this.appStateStore.datasets[this.target_vector_ds_and_field[0]]
      return dataset.object_fields[this.target_vector_ds_and_field[1]].actual_embedding_space.id
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
    delete_collection_class() {
      if (!confirm("Are you sure you want to delete this class and the list of examples?")) {
        return
      }
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/org/data_map/delete_collection_class", body)
        .then(function (response) {
          const index = that.collection.actual_classes.findIndex((collection_class) => collection_class.name === that.class_name)
          that.collection.actual_classes.splice(index, 1)
          if (that.collection.actual_classes.length === 0) {
            that.collection.actual_classes.push({
              name: "_default",
              positive_count: 0,
              negative_count: 0,
            })
          }
        })
      this.$emit("close")
    },
    get_trained_classifier() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        embedding_space_id: this.embedding_space_id,
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
        embedding_space_id: this.embedding_space_id,
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
        embedding_space_id: this.embedding_space_id,
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
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ collection.name }}:</span>
      <span class="text-medium text-gray-500">
        {{ class_name === '_default' ? 'Items' : class_name }} </span>

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
        :title="`Last retraining: ${last_retraining_human_readable}, embedding space ${embedding_space_id}`">
        <div class="absolute h-full bg-blue-500/20 rounded-md" :style="{ width: `${retraining_progress * 100}%` }"></div>
        <span class="mx-2 hover:text-blue-500">{{ is_retraining ? "Retraining..." : (show_retrain_success_label ? "Retrained ✓": "Retrain") }}</span>
      </button> -->

      <button @click="show_export_dialog = true"
        class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2 text-gray-500 font-semibold text-sm">
          Export
      </button>

      <Dialog v-model:visible="show_export_dialog" modal header="Export">
        <ExportCollectionArea :collection_id="collection_id" :class_name="class_name">
        </ExportCollectionArea>
      </Dialog>

      <button @click="show_table"
        class="rounded-md bg-green-100 hover:bg-blue-100/50 py-1 px-2 text-gray-500 font-semibold text-sm">
          Show Table
      </button>

      <button
        @click="delete_collection_class"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <!-- <InputGroup class="mb-4 mt-4">
      <InputGroupAddon>Search Intent:</InputGroupAddon>
      <InputText placeholder="Intent" v-model="collection.search_intent" />
      <Button label="Show Map" @click="show_map()"></Button>
    </InputGroup> -->

    <Dialog ref="table_dialog" v-model:visible="table_visible" maximizable modal :header="`Table: ${collection.name}`">
      <CollectionTableView
        :collection_id="collection_id"
        :class_name="class_name"
        :initial_collection="collection">
      </CollectionTableView>
    </Dialog>

    <!-- <div
      class="flex flex-row items-center justify-between text-center font-bold text-gray-400">
      <button
        v-for="item in [['positives', `Items (${class_details.positive_count})`], ['negatives', `Negatives (${class_details.negative_count})`], ['recommend', 'Recom.'], ['chat', 'Chat'], ['table', 'Table']]"
        class="flex-1"
        :class="{'text-blue-500': selected_tab === item[0]}"
        @click="selected_tab = item[0]">
        {{ item[1] }}
      </button>
    </div>
    <hr /> -->

    <CollectionItemList
      v-if="selected_tab === 'positives'"
      :is_positive="true"
      :collection_id="collection_id"
      :class_name="class_name">
    </CollectionItemList>

    <CollectionItemList
      v-if="selected_tab === 'negatives'"
      :is_positive="false"
      :collection_id="collection_id"
      :class_name="class_name">
    </CollectionItemList>

    <div v-if="selected_tab === 'recommend'">
      <br>
      <p class="text-md text-gray-700">
        The "Funnel" <br>
        Two step process:<br><br>
        1. Sort items on current map based on similarity to query / positive examples (or search full database using vector search)<br>
        2. Evalute each item using an LLM, starting with the top items<br>
        <br>
        -> Show either top-n results to the user and wait for feedback<br>
        -> or process all items that could match for an exhaustive result
      </p>
      <br>

      <button
      @click="appStateStore.recommend_items_for_collection(collection, class_name)"
      class="bg-gray-100 hover:bg-blue-100/50 text-gray-700 font-semibold rounded py-1 px-2 mb-2"
      >
        Show Map with Recommendations
      </button>
    </div>

    <ChatList
      v-if="selected_tab === 'chat'"
      :collection_id="collection_id"
      :class_name="class_name">
    </ChatList>

    <div v-if="selected_tab === 'table'">
      <br>
      <div class="flex flex-row justify-center">
        <button @click="table_visible = true; $refs.table_dialog.maximize()"
        class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2 text-gray-500 font-semibold">
          Show Table
        </button>
      </div>
      <br>

    </div>

  </div>
</template>
