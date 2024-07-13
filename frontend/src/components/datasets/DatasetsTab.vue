<script setup>
import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline"

import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DynamicDialog from 'primevue/dynamicdialog'
import OverlayPanel from "primevue/overlaypanel";
import Message from 'primevue/message';

import DatasetDetails from "./DatasetDetails.vue"
import CreateDatasetDialog from './CreateDatasetDialog.vue';

import { useToast } from 'primevue/usetoast';
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
  props: [],
  emits: [],
  data() {
    return {
      selected_dataset: null,
      shown_dataset: null,
      create_dataset_dialog_visible: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    use_single_column() {
      return window.innerWidth < 768 || (this.selected_tab === "results" && this.appStateStore.search_result_ids.length === 0)
    },
    your_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => dataset.admins.includes(this.appStateStore.user.id))
    },
    organization_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => !dataset.admins.includes(this.appStateStore.user.id) && dataset.is_public === false)
    },
    public_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => !dataset.admins.includes(this.appStateStore.user.id) && dataset.is_public === true)
    },
    categories() {
      const elements = [
        {items: this.your_datasets, name: 'Your Datasets'},
      ]
      if (!this.appStateStore.organization.is_public) {
        elements.push({items: this.organization_datasets, name: 'Shared in Organization'})
      }
      if (this.appStateStore.is_staff) {
        elements.push({items: this.public_datasets, name: 'Public'})
      }
      return elements
    },
  },
  mounted() {
  },
  watch: {
    selected_dataset() {
      // making sure a new DatasetDetails component is created when the selected dataset changes
      this.shown_dataset = null
      setTimeout(() => {
        this.shown_dataset = this.selected_dataset
      }, 100)
    },
  },
  methods: {
  },
}
</script>

<template>
  <div class="mt-3 mb-3 p-4 shadow-sm rounded-md bg-white overflow-hidden">

    <div v-if="!appState.logged_in" class="h-full flex flex-row items-center justify-center">
      <Message :closable="false">
        Log in to upload your own files (PDF, CSV, txt, etc.) to make them searchable and process them using AI.
      </Message>
    </div>

    <div v-if="appState.logged_in" class="h-full">
      <div class="h-full flex flex-row gap-4">
        <!-- left side --> <div class="flex-none w-[300px] flex flex-col gap-3 overflow-y-auto">
          <div
            v-for="category in categories"
            class="w-full rounded-md bg-gray-100 pb-2 pl-3 pr-2 pt-2">
            <div class="flex flex-row gap-3">
              <span class="font-bold text-gray-600">{{ category.name }}</span>
            </div>
            <ul class="mt-3">
              <li v-for="dataset in category.items"
                class="mb-2 flex flex-row rounded-md py-[3px] pr-2 hover:bg-blue-500/10"
                :class="{'bg-white': selected_dataset !== dataset, 'bg-blue-100': selected_dataset === dataset}">
                <button class="flex flex-1 flex-row" @click="selected_dataset = dataset">
                  <span class="pl-2 text-sm text-gray-500 text-left">
                    {{ dataset.name }}
                  </span>
                  <div class="flex-1"></div>

                </button>
              </li>
            </ul>
            <div v-if="category.items.length === 0 && category.items === your_datasets" class="mb-2 text-sm text-gray-500">
              No datasets yet, create a new one to upload your files
            </div>
            <div v-if="category.items.length === 0 && category.items !== your_datasets" class="mb-2 text-sm text-gray-500">
              No shared datasets yet
            </div>
            <Button v-if="category.items === your_datasets && appState.logged_in" class="h-6 mb-2 mt-2"
              :disabled="!appState.organization.is_member"
              @click="create_dataset_dialog_visible = true"
              label="Create new dataset">
            </Button>
            <Message v-if="category.items === your_datasets && !appState.organization.is_member" severity="warn">
              You need to be a member of the organization {{ appState.organization.name }} to create a dataset
            </Message>
            <CreateDatasetDialog
              v-if="category.items === your_datasets && create_dataset_dialog_visible"
              v-model:visible="create_dataset_dialog_visible" />
          </div>
        </div>

        <!-- right side --> <div class="flex-1 h-full flex flex-col overflow-y-auto">

          <div v-if="!selected_dataset" class="flex-1 flex flex-col items-center justify-center gap-6">
            <h2 class="text-xl font-bold text-gray-500">Upload your own files</h2>
            <div class="mx-10 text-gray-700">
              In addition to public data sources, you can upload your own files.<br>
              Those could for example be PDFs of scientific articles or CSV files with data exported from other tools.<br>
              <br>
              Uploaded data is organized in <i>datasets</i>. Each dataset has a specific data type (e.g. scientific papers) and can contain multiple files.<br>
              <br>
              We recommend using just one dataset per data type and using collections for more structure as searching across datasets has some limitations, but you can create as many datasets as you like.<br>
              <br>
              <span class="font-semibold">To start uploading data, create a new dataset.</span><br>
              <br>
              After uploading the files, you can search them in the 'explore' tab, ask them questions, add them to collections and extract information from them in tables.
            </div>
          </div>

          <DatasetDetails
            v-if="shown_dataset"
            :dataset="shown_dataset"
            @close="selected_dataset = null"
            />
        </div>
      </div>
    </div>

  </div>

</template>

<style scoped>
</style>
