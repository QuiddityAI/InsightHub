<script setup>
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
  FunnelIcon,
  HandThumbDownIcon,
  ViewColumnsIcon,
  Squares2X2Icon,
} from "@heroicons/vue/24/outline"

import Dialog from 'primevue/dialog';
import OverlayPanel from 'primevue/overlaypanel';
import Paginator from "primevue/paginator"
import Dropdown from 'primevue/dropdown';
import Checkbox from 'primevue/checkbox';

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
import CollectionSpreadsheetView from "./CollectionSpreadsheetView.vue";
import FilterBar from "./FilterBar.vue";
import SavedSearchTasksList from "./SavedSearchTasksList.vue";

import { CollectionItemSizeMode, CollectionItemLayout } from "../../utils/utils.js"

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
    'collectionStore.order_by_field'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.order_descending'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.show_irrelevant'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.per_page'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.search_mode'() {
      if (this.collectionStore.search_mode) {
        this.collectionStore.show_irrelevant = false
      }
    },
    'collectionStore.collection.items_last_changed'(new_value, old_value) {
      // nice idea, but conflicts with current approach
      // should rather check this in update_collection()
      // if (new_value > this.collectionStore.items_last_retrieved) {
      //   this.collectionStore.load_collection_items()
      // }
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
  },
  mounted() {
    if (!this.collection.ui_settings.item_size_mode) {
      this.collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.FULL})
    }
    if (!this.collection.ui_settings.item_layout) {
      this.collectionStore.update_ui_settings({item_layout: CollectionItemLayout.COLUMNS})
    }
    this.eventBus.on("collection_item_added", this.on_item_added)
    this.eventBus.on("collection_item_removed", this.on_item_removed)
    this.collectionStore.load_collection_items()
    if (this.collectionStore.collection.agent_is_running) {
      this.collectionStore.schedule_update_collection()
    }
  },
  unmounted() {
    this.eventBus.off("collection_item_added", this.on_item_added)
    this.eventBus.off("collection_item_removed", this.on_item_removed)
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
    on_item_added({collection_id, class_name, is_positive, created_item}) {
      if (collection_id === this.collectionStore.collection_id && class_name === this.collectionStore.class_name && is_positive === this.collectionStore.is_positive) {
        this.collectionStore.load_collection_items()
      }
    },
    on_item_removed({collection_id, class_name, collection_item_id}) {
      if (collection_id === this.collectionStore.collection_id && class_name === this.collectionStore.class_name) {
        const item_index = this.collectionStore.collection_items.findIndex((item) => item.id === collection_item_id)
        if (item_index >= 0) {
          this.collectionStore.collection_items.splice(item_index, 1)
        }
      }
    },
    toggle_show_irrelevant() {
      if (this.collectionStore.search_mode) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Not available in search mode', life: 2000 })
        return
      }
      this.collectionStore.show_irrelevant = !this.collectionStore.show_irrelevant
    }
  },
}
</script>

<template>
  <div class="flex flex-col overflow-hidden">

    <Dialog v-model:visible="show_search_task_dialog" modal :header="$t('CollectionView.search-task-dialog-header')">
      <SearchTaskDialog :collection="collection" :collection_class="class_name"
        @close="show_search_task_dialog = false"></SearchTaskDialog>
    </Dialog>

    <!-- Top Area -->
    <div class="flex-none pb-2 flex flex-col gap-3 overflow-hidden bg-white z-40"
      :class="{
        'shadow-md': collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET,
        'border-b': collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET,
      }">

      <!-- Heading + Action Buttons -->
      <div class="mt-3 ml-5 mr-5 flex-none flex flex-row gap-3 flex-wrap items-center">

        <ChevronLeftIcon class="h-6 w-6 text-gray-400 cursor-pointer hover:text-blue-500"
          @click="collectionStore.close_collection()">
        </ChevronLeftIcon>

        <p class="text-xl font-['Lexend'] font-medium text-black min-w-[300px] max-w-[calc(100%-520px)]"
          contenteditable @blur="collectionStore.set_collection_attributes({name: $event.target.innerText})"
          @keydown.enter="$event.target.blur()" @keydown.esc="$event.target.innerText = collection.name; $event.target.blur()"
          spellcheck="false">
          {{ collection.name }}
        </p>
        <!-- <span class="text-medium text-gray-500">
          {{ class_name === '_default' ? '' : ': ' + class_name }}
        </span> -->

        <div class="flex-1"></div>

        <BorderButton @click="(event) => { $refs.layout_dialog.toggle(event) }"
          class="h-6" v-tooltip.bottom="{ value: $t('CollectionView.change-layout'), showDelay: 400 }">
          <TableCellsIcon class="h-4 w-4"></TableCellsIcon>
        </BorderButton>

        <OverlayPanel ref="layout_dialog">
          <div class="flex flex-col gap-2 w-[140px]">
            <div class="flex flex-row">
              <BorderButton @click="collectionStore.update_ui_settings({item_layout: CollectionItemLayout.COLUMNS})" class="h-6 rounded-r-none border-r-0"
                :highlighted="collection.ui_settings.item_layout === CollectionItemLayout.COLUMNS"
                v-tooltip.bottom="{ value: $t('CollectionView.column-layout') }">
                <ViewColumnsIcon class="h-4 w-4"></ViewColumnsIcon>
              </BorderButton>
              <BorderButton @click="collectionStore.update_ui_settings({item_layout: CollectionItemLayout.GRID})" class="h-6 rounded-none"
                :highlighted="collection.ui_settings.item_layout === CollectionItemLayout.GRID"
                v-tooltip.bottom="{ value: $t('CollectionView.grid-layout') }">
                <Squares2X2Icon class="h-4 w-4"></Squares2X2Icon>
              </BorderButton>
              <BorderButton @click="collectionStore.update_ui_settings({item_layout: CollectionItemLayout.SPREADSHEET})" class="h-6 rounded-l-none border-l-0"
                :highlighted="collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET"
                v-tooltip.bottom="{ value: $t('CollectionView.spreadsheet-layout') }">
                <TableCellsIcon class="h-4 w-4"></TableCellsIcon>
              </BorderButton>
            </div>

            <div class="flex flex-row" v-if="collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET">
              <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.SMALL})" class="h-6 rounded-r-none border-r-0"
                :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.SMALL"
                v-tooltip.bottom="{ value: $t('CollectionView.item-size-small') }">
                S
              </BorderButton>
              <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.MEDIUM})" class="h-6 rounded-none"
                :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.MEDIUM"
                v-tooltip.bottom="{ value: $t('CollectionView.item-size-medium') }">
                M
              </BorderButton>
              <BorderButton @click="collectionStore.update_ui_settings({item_size_mode: CollectionItemSizeMode.FULL})" class="h-6 rounded-l-none border-l-0"
                :highlighted="collection.ui_settings.item_size_mode === CollectionItemSizeMode.FULL"
                v-tooltip.bottom="{ value: $t('CollectionView.item-size-full') }">
                L
              </BorderButton>
            </div>

            <div class="flex flex-row gap-1">
              <Checkbox v-model="collection.ui_settings.hide_checked_items_in_search"
                inputId="only_show_unchecked_in_search" :binary="true" class="scale-75"
                @change="collectionStore.update_ui_settings({hide_checked_items_in_search: collection.ui_settings.hide_checked_items_in_search}, true)" />
              <label for="only_show_unchecked_in_search" class="text-sm text-gray-500">
                {{ $t('CollectionView.hide-checked-items-in-search') }}
              </label>
            </div>
          </div>

        </OverlayPanel>

        <BorderButton @click="collectionStore.update_ui_settings({show_visibility_filters: !collection.ui_settings.show_visibility_filters})" class="h-6"
          v-tooltip.bottom="{ value: $t('CollectionView.filter-items') }" :highlighted="collection.ui_settings.show_visibility_filters">
          <FunnelIcon class="h-4 w-4"></FunnelIcon>
        </BorderButton>

        <BorderButton @click="toggle_show_irrelevant" class="h-6"
          v-tooltip.bottom="{ value: $t('CollectionView.show-items-marked-as-irrelevant') }" :highlighted="collectionStore.show_irrelevant"
          highlight_color="text-red-500">
          <HandThumbDownIcon class="h-4 w-4"></HandThumbDownIcon>
        </BorderButton>

        <BorderButton @click="delete_collection" class="h-6"
          v-tooltip.bottom="{ value: $t('CollectionView.delete-collection') }"
          hover_color="hover:text-red-500">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </BorderButton>

        <div class="h-full border-r pl-2 mr-2">
        </div>
        <BorderButton @click="show_secondary_view('summary')"
          :highlighted="collection.ui_settings.secondary_view === 'summary'" :badge="collection.writing_task_count">
          {{ $t('CollectionView.summary-secondary-view') }}
        </BorderButton>
        <BorderButton @click="show_secondary_view('map')"
          :highlighted="collection.ui_settings.secondary_view === 'map'">
          {{ $t('CollectionView.map-secondary-view') }}
        </BorderButton>
        <BorderButton @click="show_secondary_view('more')"
          :highlighted="collection.ui_settings.secondary_view === 'more'">
          {{ $t('CollectionView.more-secondary-view') }}
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
          v-tooltip.bottom="{value: $t('CollectionView.full-screen-secondary-view'), showDelay: 400}">
          <ArrowsPointingOutIcon class="h-6 w-6" v-if="!collection.ui_settings.secondary_view_is_full_screen"></ArrowsPointingOutIcon>
          <ArrowsPointingInIcon class="h-6 w-6" v-else></ArrowsPointingInIcon>
        </BorderlessButton>

        <BorderlessButton @click="collectionStore.update_ui_settings({secondary_view: null})"
          class="absolute right-3 top-3 z-50"
          v-tooltip.bottom="{value: $t('CollectionView.hide-secondary-view'), showDelay: 400}">
          <XMarkIcon class="h-6 w-6"></XMarkIcon>
        </BorderlessButton>

        <WritingTaskArea v-if="collection.ui_settings.secondary_view === 'summary'"
          class="overflow-y-auto h-full"
          :collection_id="collectionStore.collection_id" :class_name="class_name">
        </WritingTaskArea>
      </div>

      <!-- Middle: Content Area-->
      <div ref="content_area" v-if="!(collection.ui_settings.secondary_view && collection.ui_settings.secondary_view_is_full_screen)"
        class="flex-1 flex flex-col overflow-y-auto z-30 relative shadow-lg transition-[background-color]"
          :class="{
            'bg-white': collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET,
            'bg-gray-200': collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET,
          }">

        <div class="flex-none h-4 xl:h-6 w-full"
          v-if="collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET || collectionStore.search_mode || collection.agent_is_running">
        </div>

        <!-- Search / Agent Bar -->
        <div v-if="collectionStore.search_mode || collection.agent_is_running"
          class="flex-none flex flex-col gap-3 w-full px-5 mb-3 xl:mb-5">

          <div class="w-full mx-auto max-w-[700px] bg-white rounded-lg flex flex-row"
          :class="{
            'shadow-md': collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET,
            'shadow-[0_2px_6px_1px_rgba(0,0,0,0.12)]': collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET,
          }">

            <SearchModeBar v-if="collectionStore.search_mode && !collection.agent_is_running"
              @edit_search_task="show_search_task_dialog = true" />

            <AgentModeBar v-if="collection.agent_is_running" />

          </div>

        </div>

        <!-- Collection Filters -->
        <div class="flex-none flex flex-col gap-3 w-full px-5 mb-3 xl:mb-5"
          v-if="collection.filters?.length || collection.ui_settings.show_visibility_filters">
          <div class="w-full mx-auto max-w-[700px] bg-white rounded-lg flex flex-row"
            :class="{
            'shadow-md': collection.ui_settings.item_layout !== CollectionItemLayout.SPREADSHEET,
            'shadow-[0_2px_6px_1px_rgba(0,0,0,0.12)]': collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET,
            }">
            <FilterBar/>
          </div>
        </div>

        <CollectionSpreadsheetView v-if="collection.ui_settings.item_layout === CollectionItemLayout.SPREADSHEET"
          class="flex-none z-20" ref="collection_spreadsheet_view" :collection_id="collectionStore.collection_id"
          :class_name="class_name" :is_positive="true"
          :item_size_mode="collection.ui_settings.item_size_mode"
          @add_column="show_add_column_dialog = true">
        </CollectionSpreadsheetView>

        <CollectionItemGrid v-else-if="collection.ui_settings.item_layout === CollectionItemLayout.GRID"
          class="z-20" ref="collection_grid_view" :collection_id="collectionStore.collection_id"
          :class_name="class_name" :is_positive="true"
          :item_size_mode="collection.ui_settings.item_size_mode">
        </CollectionItemGrid>

        <CollectionTableView v-else
          class="z-20" ref="collection_table_view" :collection_id="collectionStore.collection_id"
          :class_name="class_name" :is_positive="true"
          :item_size_mode="collection.ui_settings.item_size_mode"
          @add_column="show_add_column_dialog = true">
        </CollectionTableView>

        <Dialog v-model:visible="show_add_column_dialog" modal :header="$t('AddColumnDialog.add-column')">
          <AddColumnDialog :collection="collection" :collection_class="class_name"
            @close="show_add_column_dialog = false">
          </AddColumnDialog>
        </Dialog>

        <div class="flex flex-row gap-5 justify-center mt-3 xl:mt-5 mb-3 xl:mb-5"
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
              @items_added="collectionStore.load_collection_items"></AddItemsToCollectionArea>
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
          class="overflow-y-auto h-full shadow-md flex flex-col gap-10 pt-12 pb-7">

          <SavedSearchTasksList>
          </SavedSearchTasksList>

          <ExplanationLog>
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
