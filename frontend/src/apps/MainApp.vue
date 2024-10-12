<script setup>

// Chart.js was replaced by ApexCharts but was still used for "Score Info" chart
// import { Chart } from "chart.js/auto"
// import annotationPlugin from "chartjs-plugin-annotation"

import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DynamicDialog from 'primevue/dynamicdialog'
// import OverlayPanel from "primevue/overlaypanel";
// import Message from 'primevue/message';

import TopMenu from "../components/general/TopMenu.vue"
import CollectionsTab from "../components/collections/CollectionsTab.vue"
import DatasetsTab from "../components/datasets/DatasetsTab.vue"
import ObjectDetailsModal from "../components/search/ObjectDetailsModal.vue"
import LegalFooter from '../components/general/LegalFooter.vue';
// import MapWithLabelsAndButtons from "../components/map/MapWithLabelsAndButtons.vue"
// import Timings from "../components/general/Timings.vue"
// import ExploreTab from "../components/search/ExploreTab.vue"
// import WriteTab from "../components/collections/WriteTab.vue"
// import ChatsTab from "../components/chats/ChatsTab.vue"
// import HoverLabel from "../components/map/HoverLabel.vue"

import { httpClient } from "../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../stores/app_state_store"
import { useMapStateStore } from "../stores/map_state_store"
import { useCollectionStore } from '../stores/collection_store';
const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

const _window = window

</script>

<script>
export default {
  inject: ["eventBus"],
  data() {
    return {
      // score_info_chart: null,
    }
  },
  methods: {
    // updateMapPassiveMargin() {
    //   if (window.innerWidth > 768) {
    //     this.mapStateStore.passiveMarginsLRTB = [
    //       window.innerWidth * 0.5 + 50,
    //       100,
    //       120,
    //       70,
    //     ]
    //   } else {
    //     this.mapStateStore.passiveMarginsLRTB = [50, 50, 250, 50]
    //   }
    // },
    evaluate_url_query_parameters() {
      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("error") !== null) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: queryParams.get("error") })
      }
      if (queryParams.get("tab")) {
        this.appStateStore.selected_app_tab = queryParams.get("tab")
      }
      // check if url has anchor #register
      if (window.location.hash === "#register") {
        this.eventBus.emit("show_register_dialog", {message: ""})
      }

      if (queryParams.get("organization_id") === null) {
        const default_organization = this.appStateStore.available_organizations.find(
          (item) => item.name === "AbsClust"
        ) || this.appStateStore.available_organizations[0]
        let best_organization_id = default_organization.id
        if (!default_organization || !default_organization.is_member) {
          for (const organization of this.appStateStore.available_organizations) {
            // get first organization where user is member
            if (organization.is_member) {
              best_organization_id = organization.id
              break
            }
          }
        }
        this.appStateStore.set_organization_id(best_organization_id, /* change_history */ false)
        const emptyQueryParams = new URLSearchParams()
        emptyQueryParams.set("organization_id", this.appStateStore.organization_id)
        history.replaceState(null, null, "?" + emptyQueryParams.toString())
      } else if (
        queryParams.get("organization_id") === String(this.appStateStore.organization_id)
      ) {
        // If this method was called because the user pressed the back arrow in the browser and
        // the dataset is the same, the stored_map might be different.
        // In this case, the datasets are still loaded and we can directly load the map:
        if (queryParams.get("map_id")) {
          this.appStateStore.show_stored_map(queryParams.get("map_id"))
        }
        if (queryParams.get("dataset_ids")) {
          const dataset_ids = queryParams.get("dataset_ids").split(",").map((x) => parseInt(x))
          this.appStateStore.settings.search.dataset_ids = dataset_ids
        }
      } else {
        // there is a new dataset_id in the parameters:
        const dataset_ids = queryParams.get("dataset_ids")?.split(",").map((x) => parseInt(x))
        this.appStateStore.set_organization_id(parseInt(queryParams.get("organization_id")), /*change history*/ false, dataset_ids)
        // if there is a map_id in the parameters, its loaded after all datasets are loaded
      }
      if (!queryParams.get("map_id") && this.appStateStore.map_id) {
        this.appStateStore.reset_search_box()
        this.appStateStore.reset_search_results_and_map()
      }
      this.collectionStore.check_url_parameters()
    },
    // show_score_info_chart() {
    //   if (this.score_info_chart) this.score_info_chart.destroy()
    //   const datasets = []
    //   const annotations = []
    //   const colors = ["red", "green", "blue", "purple", "fuchsia", "aqua", "yellow", "navy"]
    //   let i = 0
    //   let maxElements = 1
    //   for (const score_info_title in this.appStateStore.search_result_score_info) {
    //     maxElements = Math.max(
    //       maxElements,
    //       this.appStateStore.search_result_score_info[score_info_title].scores.length
    //     )
    //     datasets.push({
    //       label: score_info_title,
    //       data: this.appStateStore.search_result_score_info[score_info_title].scores,
    //       borderWidth: 1,
    //       pointStyle: false,
    //       borderColor: colors[i],
    //     })
    //     annotations.push({
    //       type: "line",
    //       mode: "vertical",
    //       xMax: this.appStateStore.search_result_score_info[score_info_title].cutoff_index,
    //       xMin: this.appStateStore.search_result_score_info[score_info_title].cutoff_index,
    //       borderColor: colors[i],
    //       label: {
    //         display: false,
    //         content: score_info_title,
    //         position: {
    //           x: "center",
    //           y: "top",
    //         },
    //       },
    //     })
    //     i += 1
    //   }
    //   this.score_info_chart = new Chart(this.$refs.score_info_chart, {
    //     type: "line",
    //     data: {
    //       labels: [...Array(maxElements).keys()],
    //       datasets: datasets,
    //     },
    //     options: {
    //       plugins: {
    //         annotation: {
    //           annotations: annotations,
    //         },
    //       },
    //     },
    //   })
    // },
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    const that = this
    this.appStateStore.initialize()
    this.appStateStore.retrieve_current_user(() => {
      this.appStateStore.retrieve_available_organizations(() => {
        this.evaluate_url_query_parameters()
        // retrieving stored maps history and collections is done in callback when organization_id is set
      })
    })
    // this.eventBus.on("datasets_are_loaded", () => {
    //   const queryParams = new URLSearchParams(window.location.search)
    //   if (queryParams.get("map_id")) {
    //     that.appStateStore.show_stored_map(queryParams.get("map_id"))
    //   }
    // })

    // this.updateMapPassiveMargin()
    // window.addEventListener("resize", this.updateMapPassiveMargin)

    window.addEventListener("popstate", this.evaluate_url_query_parameters)

    this.eventBus.on("show_table", ({collection_id, class_name}) => {
      this.appStateStore.selected_app_tab = "collections"
    })
    // this.eventBus.on("show_score_info_chart", () => {
    //   this.show_score_info_chart()
    // })

    if (window.innerWidth < 768) {
      this.appStateStore.error_dialog_message = "This application doesn't work correctly on mobile devices. Please use a desktop browser."
      this.appStateStore.show_error_dialog = true
    }
  },
  watch: {
    "appStateStore.organization_id"() {
      this.appStateStore.reset_search_results_and_map()
      this.appStateStore.retrieve_stored_maps_history_and_collections()
    },
  },
}
</script>

<template>
  <main class="relative">

    <Toast position="top-right"></Toast>
    <DynamicDialog />
    <Dialog v-model:visible="appState.show_error_dialog" modal header="Error">
      <p>{{ appState.error_dialog_message }}</p>
      <div class="mt-2 flex flex-row-reverse">
        <Button @click="appState.show_error_dialog = false" label="OK"></Button>
      </div>
    </Dialog>

    <Dialog
      v-model:visible="appState.document_details_dialog_is_visible"
      :style="{'max-width': '650px', width: '650px'}"
      @hide="appState.close_document_details">
      <ObjectDetailsModal v-if="appState.selected_document_ds_and_id"
        :initial_item="appState.selected_document_initial_item"
        :dataset="appState.selected_document_ds_and_id ? appState.datasets[appState.selected_document_ds_and_id[0]] : null"
        :show_close_button="false"></ObjectDetailsModal>
    </Dialog>

    <!-- <MapWithLabelsAndButtons v-show="appState.selected_app_tab === 'explore' && appState.map_id"></MapWithLabelsAndButtons> -->

    <!-- <Timings></Timings> -->

    <!-- content area -->
    <div class="h-screen flex flex-col pointer-events-none relative">

      <TopMenu class="flex-none pointer-events-auto relative z-50"></TopMenu>

      <!-- <ExploreTab v-show="appState.selected_app_tab === 'explore'" class="flex-1"></ExploreTab> -->

      <CollectionsTab v-show="appState.selected_app_tab === 'collections'" class="flex-1 pointer-events-auto"></CollectionsTab>

      <!-- <ChatsTab v-if="appState.selected_app_tab === 'chats'" class="flex-1 pointer-events-auto"></ChatsTab>

      <WriteTab v-if="appState.selected_app_tab === 'write'" class="flex-1 pointer-events-auto"></WriteTab> -->

      <DatasetsTab v-if="appState.selected_app_tab === 'datasets'" class="flex-1 pointer-events-auto relative"></DatasetsTab>

    </div>

    <!-- <HoverLabel class="absolute top-0 h-screen w-screen" /> -->

    <LegalFooter class="absolute z-50"
      :class="{
        'bottom-1': appState.selected_app_tab === 'explore',
        'right-3': appState.selected_app_tab === 'explore',
        'bottom-2': appState.selected_app_tab !== 'explore',
        'right-3': appState.selected_app_tab !== 'explore',
      }">
    </LegalFooter>

  </main>
</template>

<style scoped>
</style>
