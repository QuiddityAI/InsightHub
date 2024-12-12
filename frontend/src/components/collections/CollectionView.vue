<script setup>
import { httpClient } from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
  PlusIcon,
  ArchiveBoxArrowDownIcon,
  DocumentIcon,
  TableCellsIcon,
  XMarkIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
} from "@heroicons/vue/24/outline"

import Dialog from 'primevue/dialog';
import OverlayPanel from 'primevue/overlaypanel';
import Paginator from "primevue/paginator"
import Dropdown from 'primevue/dropdown';

import CollectionTableView from "./CollectionTableView.vue"
import ExportCollectionArea from "./ExportCollectionArea.vue";
import ExportTableArea from "./ExportTableArea.vue";
import AddItemsToCollectionArea from "./AddItemsToCollectionArea.vue";
import SearchTaskDialog from "./SearchTaskDialog.vue";
import AddColumnDialog from "./AddColumnDialog.vue";
import WritingTaskArea from "../summary/WritingTaskArea.vue";
import BorderButton from "../widgets/BorderButton.vue";
import BorderlessButton from "../widgets/BorderlessButton.vue";
import SearchModeBar from "../search/SearchModeBar.vue";
import AgentModeBar from "./AgentModeBar.vue";
import MapWithLabelsAndButtons from "../map/MapWithLabelsAndButtons.vue";
import CollectionItemGrid from "./CollectionItemGrid.vue";
import FilterBar from "./FilterBar.vue";

import { CollectionItemSizeMode } from "../../utils/utils.js"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store";
import { useCollectionStore } from "../../stores/collection_store"
import ExplanationLog from "./ExplanationLog.vue";

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
export default {
  inject: ["eventBus"],
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
    }
  },
  watch: {
    'collectionStore.first_index'() {
      this.collectionStore.load_collection_items()
      // scroll table to top:
      this.$refs.content_area.scrollTop = 0
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
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
    this.collectionStore.check_for_agent_status()
  },
  methods: {
    delete_collection() {
      if (!confirm("Are you sure you want to delete this collection?")) {
        return
      }
      this.collectionStore.delete_collection(this.collectionStore.collection_id)
    },
    show_map() {
      this.appStateStore.reset_search_box()
      this.appStateStore.settings.search.all_field_query = this.collection.search_intent
      this.appStateStore.request_search_results()
    },
    show_secondary_view(view) {
      let new_secondary_view = this.collection.ui_settings.secondary_view === view ? null : view
      this.collectionStore.update_ui_settings({secondary_view: new_secondary_view})
    },
  },
}
</script>

<template>
  <div class="flex flex-col overflow-hidden">

    <Dialog v-model:visible="show_search_task_dialog" modal header="Search Task">
      <SearchTaskDialog :collection="collection" :collection_class="class_name"
        @close="show_search_task_dialog = false; collectionStore.check_for_agent_status()"></SearchTaskDialog>
    </Dialog>

    <!-- Top Area -->
    <div class="flex-none pb-2 flex flex-col gap-3 overflow-hidden bg-white shadow-md z-40">

      <!-- Heading + Action Buttons -->
      <div class="mt-3 ml-5 mr-5 flex-none flex flex-row gap-3 flex-wrap items-center">

        <ChevronLeftIcon class="h-6 w-6 text-gray-400 cursor-pointer hover:text-blue-500"
          @click="collectionStore.close_collection()">
        </ChevronLeftIcon>

        <p class="text-xl font-serif font-bold text-black min-w-[300px] max-w-[calc(100%-520px)]">
          {{ collection.name }}
        </p>
        <!-- <span class="text-medium text-gray-500">
          {{ class_name === '_default' ? '' : ': ' + class_name }}
        </span> -->

        <div class="flex-1"></div>

        <div class="flex flex-row">
          <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.SINGLE_LINE})" class="h-6 rounded-r-none border-r-0"
            :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.SINGLE_LINE"
            v-tooltip.bottom="{ value: 'Single Line Items' }">
            S
          </BorderButton>
          <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.SMALL})" class="h-6 rounded-none"
            :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.SMALL"
            v-tooltip.bottom="{ value: 'Small Items' }">
            M
          </BorderButton>
          <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.FULL})" class="h-6 rounded-l-none border-l-0"
            :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.FULL"
            v-tooltip.bottom="{ value: 'Full Items' }">
            L
          </BorderButton>
        </div>

        <BorderButton @click="collectionStore.update_ui_settings({use_grid_view: !collection.ui_settings.use_grid_view})" class="h-6"
          v-tooltip.bottom="{ value: 'Use grid view' }" :highlighted="collection.ui_settings.use_grid_view">
          <TableCellsIcon class="h-4 w-4"></TableCellsIcon>
        </BorderButton>

        <BorderButton @click="delete_collection" class="h-6"
          v-tooltip.bottom="{ value: 'Delete collection' }"
          hover_color="hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </BorderButton>

        <span class="text-gray-400">
          Views:
        </span>
        <BorderButton @click="show_secondary_view('summary')"
          :highlighted="collection.ui_settings.secondary_view === 'summary'" :badge="collection.writing_task_count">
          Summary
        </BorderButton>
        <BorderButton @click="show_secondary_view('map')"
          :highlighted="collection.ui_settings.secondary_view === 'map'">
          Map
        </BorderButton>
        <BorderButton @click="show_secondary_view('more')"
          :highlighted="collection.ui_settings.secondary_view === 'more'">
          More
        </BorderButton>
      </div>
    </div>

    <!-- Lower Area -->
    <div class="flex-1 flex flex-row overflow-hidden z-30 relative">

      <!-- Left Side: Summary -->
      <div v-if="collection.ui_settings.secondary_view === 'summary'"
        class="flex-none bg-white shadow-md z-40 relative transition-[width]"
        :class="{'w-[620px]': !collection.ui_settings.secondary_view_is_full_screen,
          'w-full': collection.ui_settings.secondary_view_is_full_screen, }">

        <BorderlessButton @click="collectionStore.update_ui_settings({secondary_view_is_full_screen: !collection.ui_settings.secondary_view_is_full_screen})"
          class="absolute right-12 top-3 z-50"
          v-tooltip.bottom="{value: 'Full Screen', showDelay: 400}">
          <ArrowsPointingOutIcon class="h-6 w-6" v-if="!collection.ui_settings.secondary_view_is_full_screen"></ArrowsPointingOutIcon>
          <ArrowsPointingInIcon class="h-6 w-6" v-else></ArrowsPointingInIcon>
        </BorderlessButton>

        <BorderlessButton @click="collectionStore.update_ui_settings({secondary_view: null})"
          class="absolute right-3 top-3 z-50"
          v-tooltip.bottom="{value: 'Hide', showDelay: 400}">
          <XMarkIcon class="h-6 w-6"></XMarkIcon>
        </BorderlessButton>

        <WritingTaskArea v-if="collection.ui_settings.secondary_view === 'summary'"
          class="overflow-y-auto h-full"
          :collection_id="collectionStore.collection_id" :class_name="class_name">
        </WritingTaskArea>
      </div>

      <!-- Middle: Content Area-->
      <div ref="content_area" v-if="!(collection.ui_settings.secondary_view && collection.ui_settings.secondary_view_is_full_screen)"
        class="flex-1 flex flex-col gap-3 xl:gap-5 overflow-y-auto pt-4 xl:pt-6 z-30 relative shadow-lg bg-gray-200">

        <!-- Search / Agent Bar -->
        <div v-if="collectionStore.search_mode || collection.agent_is_running"
          class="flex-none flex flex-col gap-3 w-full px-5">

          <div class="w-full mx-auto max-w-[700px] bg-white rounded-lg shadow-md flex flex-row">

            <SearchModeBar v-if="collectionStore.search_mode && !collection.agent_is_running"
              @edit_search_task="show_search_task_dialog = true" />

            <AgentModeBar v-if="collection.agent_is_running" />

          </div>

          <div class="w-full mx-auto max-w-[700px] bg-white rounded-lg shadow-md flex flex-row"
            v-if="collection.filters?.length">
            <FilterBar
              @edit_search_task="show_search_task_dialog = true" />
          </div>
        </div>

        <CollectionTableView v-if="!collection.ui_settings.use_grid_view"
          class="z-20" ref="collection_table_view" :collection_id="collectionStore.collection_id"
          :class_name="class_name" :is_positive="true"
          :item_size_mode="collection.ui_settings.item_size_mode"
          @add_column="show_add_column_dialog = true">
        </CollectionTableView>

        <CollectionItemGrid v-if="collection.ui_settings.use_grid_view"
          class="z-20" ref="collection_grid_view" :collection_id="collectionStore.collection_id"
          :class_name="class_name" :is_positive="true"
          :item_size_mode="collection.ui_settings.item_size_mode">
        </CollectionItemGrid>

        <Dialog v-model:visible="show_add_column_dialog" modal header="Add Column">
          <AddColumnDialog :collection="collection" :collection_class="class_name"
            @close="show_add_column_dialog = false">
          </AddColumnDialog>
        </Dialog>

        <div class="flex flex-row gap-5 justify-center"
            v-if="!collectionStore.search_mode && !collection.agent_is_running">
          <BorderButton @click="show_search_task_dialog = true"
            class="py-1 bg-white rounded-xl shadow-md">
            <PlusIcon class="inline h-4 w-4"></PlusIcon> Items by search
          </BorderButton>

          <BorderButton @click="show_add_item_dialog = true"
            class="py-1 bg-white rounded-xl shadow-md">
            <PlusIcon class="inline h-4 w-4"></PlusIcon> Items manually
          </BorderButton>
          <Dialog v-model:visible="show_add_item_dialog" modal header="Add Items Manually">
            <AddItemsToCollectionArea :collection="collection" :collection_class="class_name"
              @items_added="$refs.collection_table_view.load_collection_items"></AddItemsToCollectionArea>
          </Dialog>
        </div>

        <div class="flex-1"></div>

        <div class="w-full pl-4 pr-2 flex flex-row gap-2 flex-wrap items-center bg-white border-t">
          <BorderButton @click="show_export_dialog = true" class="h-6"
            v-tooltip.top="{ value: 'Export items only' }">
            <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
            <DocumentIcon class="h-4 w-4 inline" />
          </BorderButton>
          <Dialog v-model:visible="show_export_dialog" modal header="Export">
            <ExportCollectionArea :collection_id="collectionStore.collection_id" :class_name="class_name">
            </ExportCollectionArea>
          </Dialog>

          <BorderButton @click="event => { $refs.export_dialog.toggle(event) }" class="h-6"
            v-tooltip.top="{ value: 'Export table' }">
            <ArchiveBoxArrowDownIcon class="h-4 w-4 mr-2 inline" />
            <TableCellsIcon class="h-4 w-4 inline" />
          </BorderButton>
          <OverlayPanel ref="export_dialog">
            <ExportTableArea :collection_id="collectionStore.collection_id" :class_name="class_name">
            </ExportTableArea>
          </OverlayPanel>

          <div class="flex-1"></div>

          <Paginator v-model:first="collectionStore.first_index" :rows="collectionStore.per_page"
            :total-records="collectionStore.filtered_count"
            class="mt-[0px]"></Paginator>
          <Dropdown v-if="!collectionStore.search_mode"
            v-model="collectionStore.order_by_field"
            :options="collectionStore.available_order_by_fields"
            optionLabel="name"
            optionValue="identifier"
            placeholder="Order By..."
            class="w-40 mr-2 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
          <button v-if="!collectionStore.search_mode"
            @click="collectionStore.order_descending = !collectionStore.order_descending"
            v-tooltip="{'value': 'Sort Order', showDelay: 500}"
            class="w-8 h-8 text-sm text-gray-400 rounded bg-white border border-gray-300 hover:bg-gray-100">
            {{ collectionStore.order_descending ? '▼' : '▲' }}
          </button>
          <div class="flex-1"></div>
        </div>

      </div>

      <!-- Right Side: More / Map -->
      <div v-if="collection.ui_settings.secondary_view && collection.ui_settings.secondary_view !== 'summary'"
        class="flex-none bg-white relative"
        :class="{
          'z-0': collection.ui_settings.secondary_view === 'map',
          'z-40': collection.ui_settings.secondary_view === 'more',
          'w-[600px]': !collection.ui_settings.secondary_view_is_full_screen,
          'w-full': collection.ui_settings.secondary_view_is_full_screen,
          }">

        <BorderlessButton @click="collectionStore.update_ui_settings({secondary_view_is_full_screen: !collection.ui_settings.secondary_view_is_full_screen})"
          class="absolute left-12 top-3 z-50"
          v-tooltip.bottom="{value: 'Full Screen', showDelay: 400}">
          <ArrowsPointingOutIcon class="h-6 w-6" v-if="!collection.ui_settings.secondary_view_is_full_screen"></ArrowsPointingOutIcon>
          <ArrowsPointingInIcon class="h-6 w-6" v-else></ArrowsPointingInIcon>
        </BorderlessButton>

        <BorderlessButton @click="collectionStore.update_ui_settings({secondary_view: null})"
          class="absolute left-3 top-3 z-50"
          v-tooltip.bottom="{value: 'Hide', showDelay: 400}">
          <XMarkIcon class="h-6 w-6"></XMarkIcon>
        </BorderlessButton>

        <div v-if="collection.ui_settings.secondary_view === 'more'"
          class="overflow-hidden h-full shadow-md">
          <ExplanationLog class="h-full overflow-y-auto">
          </ExplanationLog>
        </div>

        <div v-if="collection.ui_settings.secondary_view === 'map'"
          class="w-full h-full relative">
          <MapWithLabelsAndButtons class="w-full h-full">
          </MapWithLabelsAndButtons>
        </div>
      </div>

    </div>

  </div>
</template>
