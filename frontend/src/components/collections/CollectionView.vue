<script setup>
import { httpClient } from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
  ArchiveBoxArrowDownIcon,
  DocumentIcon,
  TableCellsIcon,
  PlusIcon,
} from "@heroicons/vue/24/outline"

import Dialog from 'primevue/dialog';
import OverlayPanel from 'primevue/overlaypanel';
import Message from "primevue/message";

import CollectionTableView from "./CollectionTableView.vue"
import ExportCollectionArea from "./ExportCollectionArea.vue";
import ExportTableArea from "./ExportTableArea.vue";
import AddItemsToCollectionArea from "./AddItemsToCollectionArea.vue";
import SearchTaskDialog from "./SearchTaskDialog.vue";
import AddColumnDialog from "./AddColumnDialog.vue";
import WritingTaskArea from "./WritingTaskArea.vue";


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
      collection: useAppStateStore().collections.find((collection) => collection.id === this.collection_id),
      trained_classifier: null,
      is_retraining: false,
      retraining_progress: 0.0,
      show_retrain_success_label: false,
      table_visible: false,
      show_export_dialog: false,

      show_search_task_dialog: false,
      show_add_column_dialog: false,
      show_add_item_dialog: false,

      right_side_view: null,  // one of 'chart', 'map', 'summary'
    }
  },
  watch: {
  },
  computed: {
    ...mapStores(useAppStateStore),
    class_details() {
      return this.collection.actual_classes.find((collection_class) => collection_class.name === this.class_name)
    }
  },
  mounted() {
    this.check_for_agent_status()
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
    check_for_agent_status() {
      const that = this
      if (this.collection.agent_is_running) {
        setTimeout(() => {
          that.appStateStore.update_collection(that.collection_id, (collection) => {
            that.check_for_agent_status()
          })
        }, 500)
      }
    },
    show_map() {
      this.appStateStore.reset_search_box()
      this.appStateStore.settings.search.all_field_query = this.collection.search_intent
      this.appStateStore.request_search_results()
    },
    show_right_side_view(view) {
      if (this.right_side_view === view) {
        this.right_side_view = null
        return
      }
      this.right_side_view = view
    },
  },
}
</script>

<template>
  <div class="flex flex-col overflow-hidden">

    <div class="flex-none pb-2 flex flex-col gap-3 overflow-hidden bg-white shadow-md z-40">

      <div class="mt-3 ml-5 mr-5 flex-none flex flex-row gap-3">

        <span class="text-xl font-serif font-bold text-black">{{ collection.name }}</span>
        <!-- <span class="text-medium text-gray-500">
          {{ class_name === '_default' ? '' : ': ' + class_name }}
        </span> -->
      </div>

      <!-- -------------------------------------------------------------- -->

      <div class="ml-5 mr-5 flex flex-row gap-3 mb-1">

        <button class="text-sm font-bold text-gray-800 border border-gray-200 rounded-md px-2 hover:text-blue-500"
          @click="show_search_task_dialog = true">
          <PlusIcon class="inline h-4 w-4"></PlusIcon> Items by search
        </button>
        <Dialog v-model:visible="show_search_task_dialog" modal header="Search Task">
          <SearchTaskDialog :collection="collection" :collection_class="class_name"
            @close="show_search_task_dialog = false"></SearchTaskDialog>
        </Dialog>

        <button @click="show_add_item_dialog = true"
          class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50">
          <PlusIcon class="inline h-4 w-4"></PlusIcon> Items manually
        </button>
        <Dialog v-model:visible="show_add_item_dialog" modal header="Add Items">
          <AddItemsToCollectionArea :collection="collection" :collection_class="class_name"
            @items_added="$refs.collection_table_view.load_collection_items"></AddItemsToCollectionArea>
        </Dialog>

        <button @click="show_add_column_dialog = true"
          class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50">
          <PlusIcon class="inline h-4 w-4"></PlusIcon> Column
        </button>
        <Dialog v-model:visible="show_add_column_dialog" modal header="Add Column">
          <AddColumnDialog :collection="collection" :collection_class="class_name"
            :collection_items="$refs.collection_table_view.collection_items" @close="show_add_column_dialog = false">
          </AddColumnDialog>
        </Dialog>

        <div class="flex-1"></div>

        <button @click="show_export_dialog = true" v-tooltip.bottom="{ value: 'Export items only' }"
          class="rounded-md bg-gray-100 hover:bg-blue-100/50 py-1 px-2 text-gray-500 font-semibold text-sm">
          <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
          <DocumentIcon class="h-4 w-4 inline" />
        </button>
        <Dialog v-model:visible="show_export_dialog" modal header="Export">
          <ExportCollectionArea :collection_id="collection_id" :class_name="class_name">
          </ExportCollectionArea>
        </Dialog>

        <button @click="event => { $refs.export_dialog.toggle(event) }" v-tooltip.bottom="{ value: 'Export table' }"
          class="py-1 px-2 rounded-md bg-gray-100 text-gray-500 text-sm font-semibold hover:bg-blue-100/50">
          <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
          <TableCellsIcon class="h-4 w-4 inline" />
        </button>
        <OverlayPanel ref="export_dialog">
          <ExportTableArea :collection_id="collection_id" :class_name="class_name">
          </ExportTableArea>
        </OverlayPanel>

        <button @click="delete_collection" v-tooltip.bottom="{ value: 'Delete collection' }"
          class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>

        <div class="flex-1"></div>

        <span class="text-gray-400">
          Views:
        </span>
        <button v-if="appState.user.is_staff" @click="show_right_side_view('chart')"
          class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
          :class="{'text-blue-500': right_side_view === 'chart'}">
          Chart
        </button>
        <button v-if="appState.user.is_staff" @click="show_right_side_view('map')"
          class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
          :class="{'text-blue-500': right_side_view === 'map'}">
          Map
        </button>
        <button v-if="appState.user.is_staff" @click="show_right_side_view('summary')"
          class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
          :class="{'text-blue-500': right_side_view === 'summary'}">
          Summary
        </button>
      </div>

      <Message v-if="collection.agent_is_running"
        class="mx-5 -mt-0 mb-1"
        severity="info">
        Agent is running: {{ collection.current_agent_step }}
      </Message>

    </div>

    <!-- -------------------------------------------------------------- -->

    <div class="flex-1 overflow-hidden flex flex-row">
      <CollectionTableView class="pl-3 pt-2 z-20" ref="collection_table_view" :collection_id="collection_id"
        :class_name="class_name" :is_positive="true">
      </CollectionTableView>

      <div v-if="right_side_view"
        class="flex-none pt-5 w-[500px] bg-white shadow-md z-30">

        <div v-if="right_side_view === 'chart'"
          class="p-3">
          Chart
        </div>

        <div v-if="right_side_view === 'map'"
          class="p-3">
          Map
        </div>

        <WritingTaskArea v-if="right_side_view === 'summary'"
          class=""
          :collection_id="collection_id" :class_name="class_name">
        </WritingTaskArea>
      </div>
    </div>

  </div>
</template>
