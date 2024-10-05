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
import WritingTaskArea from "../summary/WritingTaskArea.vue";
import BorderButton from "../widgets/BorderButton.vue";
import SearchModeBar from "../search/SearchModeBar.vue";
import AgentModeBar from "./AgentModeBar.vue";


import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
export default {
  props: [],
  emits: [],
  data() {
    return {
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
    'collectionStore.collection.writing_task_count'() {
      if (this.collection?.writing_task_count > 0) {
        this.right_side_view = 'summary'
      }
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collection() {
      return this.collectionStore.collection
    },
    class_name() {
      return this.collectionStore.class_name
    },
    class_details() {
      return this.collection.actual_classes.find((collection_class) => collection_class.name === this.class_name)
    },
    search_mode() {
      return this.$refs.collection_table_view?.search_mode
    },
  },
  mounted() {
    this.check_for_agent_status()
    if (this.collection.writing_task_count > 0) {
      this.right_side_view = 'summary'
    }
  },
  methods: {
    delete_collection() {
      if (!confirm("Are you sure you want to delete this collection?")) {
        return
      }
      this.collectionStore.delete_collection(this.collectionStore.collection_id)
    },
    check_for_agent_status() {
      const that = this
      if (this.collection.agent_is_running) {
        setTimeout(() => {
          that.collectionStore.update_collection((collection) => {
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

      <!-- Heading -->
      <div class="mt-3 ml-5 mr-5 flex-none flex flex-row gap-3 items-center">

        <ChevronLeftIcon class="h-6 w-6 text-gray-400 cursor-pointer hover:text-blue-500"
          @click="collectionStore.close_collection()">
        </ChevronLeftIcon>

        <span class="text-xl font-serif font-bold text-black">{{ collection.name }}</span>
        <!-- <span class="text-medium text-gray-500">
          {{ class_name === '_default' ? '' : ': ' + class_name }}
        </span> -->

        <div class="flex-1"></div>

        <BorderButton @click="show_export_dialog = true" class="h-6"
          v-tooltip.bottom="{ value: 'Export items only' }">
          <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
          <DocumentIcon class="h-4 w-4 inline" />
        </BorderButton>
        <Dialog v-model:visible="show_export_dialog" modal header="Export">
          <ExportCollectionArea :collection_id="collectionStore.collection_id" :class_name="class_name">
          </ExportCollectionArea>
        </Dialog>

        <BorderButton @click="event => { $refs.export_dialog.toggle(event) }" class="h-6"
          v-tooltip.bottom="{ value: 'Export table' }">
          <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
          <TableCellsIcon class="h-4 w-4 inline" />
        </BorderButton>
        <OverlayPanel ref="export_dialog">
          <ExportTableArea :collection_id="collectionStore.collection_id" :class_name="class_name">
          </ExportTableArea>
        </OverlayPanel>

        <BorderButton @click="delete_collection" class="h-6"
          v-tooltip.bottom="{ value: 'Delete collection' }"
          hover_color="hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </BorderButton>
      </div>

      <!-- Toolbar -->
      <div class="ml-5 mr-5 flex flex-row gap-3 mb-1 items-end h-7">

        <BorderButton @click="show_search_task_dialog = true" v-if="!collectionStore.search_mode && !collection.agent_is_running">
          <PlusIcon class="inline h-4 w-4"></PlusIcon> Items by search
        </BorderButton>
        <Dialog v-model:visible="show_search_task_dialog" modal header="Search Task">
          <SearchTaskDialog :collection="collection" :collection_class="class_name"
            @close="show_search_task_dialog = false; check_for_agent_status()"></SearchTaskDialog>
        </Dialog>

        <BorderButton @click="show_add_item_dialog = true" v-if="!collectionStore.search_mode && !collection.agent_is_running">
          <PlusIcon class="inline h-4 w-4"></PlusIcon> Items manually
        </BorderButton>
        <Dialog v-model:visible="show_add_item_dialog" modal header="Add Items">
          <AddItemsToCollectionArea :collection="collection" :collection_class="class_name"
            @items_added="$refs.collection_table_view.load_collection_items"></AddItemsToCollectionArea>
        </Dialog>

        <SearchModeBar v-if="collectionStore.search_mode"
          @edit_search_task="show_search_task_dialog = true" />

        <AgentModeBar v-if="collection.agent_is_running" />

        <div class="flex-1"></div>

        <span class="text-gray-400">
          Views:
        </span>
        <BorderButton v-if="appState.user.is_staff" @click="show_right_side_view('chart')"
          :highlighted="right_side_view === 'chart'">
          Chart
        </BorderButton>
        <BorderButton v-if="appState.user.is_staff" @click="show_right_side_view('map')"
          :highlighted="right_side_view === 'map'">
          Map
        </BorderButton>
        <BorderButton v-if="appState.user.is_staff" @click="show_right_side_view('summary')"
          :highlighted="right_side_view === 'summary'">
          Summary
        </BorderButton>
      </div>

    </div>

    <!-- -------------------------------------------------------------- -->

    <div class="flex-1 overflow-hidden flex flex-row">

      <CollectionTableView class="z-20 bg-gray-200" ref="collection_table_view" :collection_id="collectionStore.collection_id"
        :class_name="class_name" :is_positive="true"
        @add_column="show_add_column_dialog = true">
      </CollectionTableView>

      <Dialog v-model:visible="show_add_column_dialog" modal header="Add Column">
        <AddColumnDialog :collection="collection" :collection_class="class_name"
          :collection_items="$refs.collection_table_view.collection_items" @close="show_add_column_dialog = false">
        </AddColumnDialog>
      </Dialog>

      <div v-if="right_side_view"
        class="flex-none w-[600px] bg-white shadow-md z-30">

        <div v-if="right_side_view === 'chart'"
          class="p-3">
          Chart
        </div>

        <div v-if="right_side_view === 'map'"
          class="p-3">
          Map
        </div>

        <WritingTaskArea v-if="right_side_view === 'summary'"
          class="overflow-y-auto h-full"
          :collection_id="collectionStore.collection_id" :class_name="class_name">
        </WritingTaskArea>
      </div>
    </div>

  </div>
</template>
