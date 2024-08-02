<script setup>
import {
  CursorArrowRaysIcon,
} from "@heroicons/vue/24/outline"

import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DynamicDialog from 'primevue/dynamicdialog'
import OverlayPanel from "primevue/overlaypanel";
import Message from 'primevue/message';
import ProgressSpinner from "primevue/progressspinner";

import CreateSearchTaskArea from "../search/CreateSearchTaskArea.vue"
import SearchTaskDescriptionCard from "../search/SearchTaskDescriptionCard.vue"
import CollectionQuickAccessCard from "../search/CollectionQuickAccessCard.vue"

import ResultList from "../search/ResultList.vue"
import ObjectDetailsModal from "../search/ObjectDetailsModal.vue"
import CollectionItem from "../collections/CollectionItem.vue"

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
      show_summary_dialog: false,
      show_tutorial_video_dialog: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    use_single_column() {
      return window.innerWidth < 768
    },
    show_result_area() {
      return this.appStateStore.search_result_ids.length || this.appStateStore.map_id || this.appStateStore.is_loading_search_results
    },
  },
  mounted() {
    this.eventBus.on("show_summary_dialog", () => {
      this.show_summary_dialog = true
    })
    setTimeout(() => {
      this.show_tutorial_video_dialog = !this.appStateStore.logged_in || this.appStateStore.user?.used_ai_credits === 0
    }, 1000)
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col items-center justify-center">

    <div v-if="!show_result_area" class="flex flex-col items-center justify-center w-[900px]">
      <div class="mb-[40px] max-w-lg"
        v-if="appState.settings.search.task_type === null && (appState.organization?.workspace_tool_logo_url || appState.organization?.workspace_tool_intro_text)">
        <div
          class="align-center flex flex-1 flex-col justify-center">
          <div class="mb-6 flex flex-row justify-center">
            <img
              class="h-12"
              :src="appState.organization ? appState.organization.workspace_tool_logo_url : ''" />
          </div>
          <div
            class="mb-2 flex-none text-center pointer-events-auto font-bold text-gray-400"
            v-html="appState.organization ? appState.organization.workspace_tool_intro_text : ''"></div>
        </div>
      </div>

      <CreateSearchTaskArea class="flex-none"></CreateSearchTaskArea>

      <Dialog v-model:visible="show_tutorial_video_dialog"
        :modal="false" position="topright" class="mt-20 mr-12"
        :style="{ width: '200px' }">
        <a class="flex flex-col items-center gap-1" href="https://drive.google.com/file/d/1li_hlCJG1VxGTU2dCFN82BYoZ0PtAYDY/view?usp=sharing" target="_blank">
          <img class="w-48" src="https://lh3.googleusercontent.com/fife/ALs6j_FA5omo5J6ZIZjmubcQOf_MoJ5KoX3FfCptuKiFv-2qQgDR6VAHQzp3JOpH0apaSIIBFKyX-AEn-1grQyPYnGl454AbhiW7u-0y1NiVn-0ktMaJKcqPLstEHri2C77rBclCL6toQTrNE4ua56l7qqtMXRZZSIOB38bLAKAbMmLbGhTokamfvlPhWhcDjLiWO3_pGOi_1Y9jRj7m2Hrj0bwaN3YgD7_sfZzuY94JRi7xfSOCpvifuWvOcQuuI5zBT3iO8sFq3nHlWZzc5c0l9Xq0_hGwuqU-L-hSu6QAj72FXhiN9MrEQzSjVVbJ0caVNzdUF7I5ffJls8koQfEUEm5OzsYido-kbmOz5d7iJxSrNhR96tSZ3D7wterJQ7louAriC32U5toWFpw0qROq0SqNHHEY-MVf7SO0ys8GRz3is2LoYE5RJNp5qa1IilTpN_0xdqzuUwHyXQc1No7dUMk8Io324ggDYI29DKA9ZOB-F0jgvtkHpuk9VOTOdfAAUo3wJ1NAJhc8BKsJbGQaeR89H9ydzI1SaZd48dBJPhnav5mEYg5J8rqA-n4eqwB0SEzohy2zByi_zH8XIzmrwrwR0IIRfUphgurPO2VmbKJEaWZyqRg7Sm5gCc7c1R2AnbrnS9h3sO3rmcfoSZsg31A8t4ZjGa42d7NDoJIVwCJuaD6RsgOkCDKXqfBc9uxM1hVNtAXVDZTiaPwbSE2PJd6OldlXMmLkHlwDI4Bghg92Kw9lRz_38j7NOJcrBlldgCVjJQov0z-TadRk7ME0EII7iwgpkzkat-8em1jjykMLoPExyqGYPrtNGXL5OoI91ccld8o_iGKv8-070W-6LUNnpUBpMfzRget-uGGYSvEsi1wX_3H4cei2HDQxKvqZgwuMYDjkhuxjjz_nlTPw4XMmlJHjxWyf0Z26X0l0zWMlmL3DuvSn4GuwnKgTGYI1QCOAAGPNVpGbV1mQizitn-_FhprLAf1DKNUPghoVSiKpTWKX0zfL7wNta4pbv-ia8Xj9IFGiO6OOoqhtks1jqnmrmfi0WCyCLUjefe3nE3aRGev4sQDUS8dCqr7-Cb7Ol_SMlSRfE0t_dz_iXKVwubY2KOeMGhist4UI-R9CUf1XqqilSWrr3i6QJ4AyGAbcc3d1XHqL9w-xmutRQaWjHYNCHugb9Acs-1VExN0WruHZFquElxNykCP82sZbTQpqtJXL8bD4ITVfGb3e5EPIAMH9W753sd6DzEl5ZK_f5h99pyR6k44wdprymmMYiatjmp79g7vW2FPWhVbntoxv9EPuB4lth3sBM1G0FCPUI4vqwoU0LgwhsEwJxQsN4wRGye5VM3Lmo-EYhOmsyUPbp_XY7bim_YdB63El2ljQi1Y_J71ncLSzSylieZ2fmS48UiesuHI6OpAtv7BzxTPnKQxdGailT2vdnTuCuN-6BPm1RMyb2IWA2JxYBeWa-edIr9XQm7mc9-lSZlNL1XAblWPTNvKcl7pyNYQm2WTTTb-1aafIPD1ZRxbrVcXKAVKJUBGKJRk-jAudeobeX3ADGC-ZgS33zJeNJl2DbRei5ymK-naRzOtEdL8i5frjB08b7x0uDhsv0n0-WwE2qg=w1920-h1080-k-pd" />
          <p class="text-gray-600 text-sm mt-2">Learn the basics in 60s</p>
        </a>
      </Dialog>
    </div>

    <!-- two column layout (search results left and map and details card right)-->
    <div v-else
      class="w-full grid min-h-0 min-w-0 mt-3 gap-4"
      :class="{
        'grid-cols-1': use_single_column,
        'grid-cols-2': !use_single_column,
      }"
      style="grid-auto-rows: minmax(auto, min-content)">

      <!-- left column -->
      <div ref="left_column" class="h-[calc(100vh-6em)] pointer-events-none flex flex-col gap-3">

        <SearchTaskDescriptionCard class="pointer-events-auto">

        </SearchTaskDescriptionCard>

        <div class="flex-1 min-h-0 px-3 pt-1 bg-white shadow-sm rounded-md pointer-events-auto overflow-y-auto" style="min-height: 0">

          <div v-if="appState.debug_autocut">
            <canvas ref="score_info_chart"></canvas>
            <div v-if="search_result_score_info">
              <div
                v-for="score_info_title in Object.keys(search_result_score_info)"
                class="text-xs">
                {{ score_info_title }} <br />
                Max score:
                {{ search_result_score_info[score_info_title].max_score.toFixed(2) }}, Min
                score:
                {{ search_result_score_info[score_info_title].min_score.toFixed(2) }},
                Cutoff Index:
                {{ search_result_score_info[score_info_title].cutoff_index }}, Reason:
                {{ search_result_score_info[score_info_title].reason }}
                <div
                  v-for="item_id in search_result_score_info[score_info_title]
                    .positive_examples"
                  :key="'example' + item_id"
                  class="justify-between pb-3">
                  <CollectionItem :item_id="item_id" :is_positive="true">
                  </CollectionItem>
                </div>
                <div
                  v-for="item_id in search_result_score_info[score_info_title]
                    .negative_examples"
                  :key="'example' + item_id"
                  class="justify-between pb-3">
                  <CollectionItem :item_id="item_id" :is_positive="false">
                  </CollectionItem>
                </div>
              </div>
            </div>
          </div>

          <!-- Cluster selection: -->
          <!-- <div
            v-if="appState.search_result_ids.length !== 0 && appState.cluster_data.length !== 0"
            class="ml-2 mt-1 flex flex-row items-center">
            <span class="mr-2 flex-none text-gray-500">Cluster:</span>
            <div class="flex-1 h-10">
              <select
                v-model="appState.selected_cluster_id"
                class="w-full h-[90%] text-md flex-1 rounded border-transparent text-gray-500 focus:border-blue-500 focus:ring-blue-500">
                <option :value="null" selected>All</option>
                <option v-for="cluster in appState.cluster_data" :value="cluster.id" selected>
                  {{ cluster.title }}
                </option>
              </select>
            </div>
          </div> -->

          <ResultList></ResultList>

        </div>

        <!-- <CollectionQuickAccessCard></CollectionQuickAccessCard> -->

      </div>

      <!-- right column (e.g. for showing box with details for selected result) -->
      <div
        ref="right_column"
        class="pointer-events-none flex flex-col"
        :class="{'h-screen': !use_single_column}">

        <div
          v-if="appState.selected_document_ds_and_id !== null && appState.selected_app_tab === 'explore'"
          class="pointer-events-auto rounded-md bg-white p-4 shadow-xl max-h-[75vh]">
          <ObjectDetailsModal
            class="h-full w-full"
            :initial_item="appState.get_item_by_ds_and_id(appState.selected_document_ds_and_id)"
            :dataset="appState.datasets[appState.selected_document_ds_and_id[0]]"
            :show_close_button="true"></ObjectDetailsModal>
        </div>

        <div
          v-if="show_summary_dialog"
          class="pointer-events-auto rounded-md bg-white p-4 shadow-xl max-h-[75vh]">
          <div class="flex flex-row">
            <h3 class="text-gray-700 font-semibold">{{ mapState.map_parameters?.search.question }}</h3>
            <div class="flex-1"></div>
            <button @click="show_summary_dialog = false" class="text-gray-500">X</button>
          </div>
          <div class="mt-2">
            <p class="text-gray-600 text-sm">
              {{ mapState.answer?.answer.replace(/\[.*\]/g, " ")}}
            </p>
          </div>
          <!-- <p class="mt-3 mb-1 text-gray-600 text-md font-semibold">Cluster 1: Membranes</p>
          <p class="text-gray-600 text-md text-sm">The articles in this cluster analyze how Mxenes can be used for high-tech membranes. Most of them conduct experiments on how durable those membranes are [1] [2].</p> -->
        </div>

        <div v-if="appState.show_loading_bar || appState.is_loading_search_results" class="flex w-full flex-1 flex-col justify-center items-center">
          <div class="flex flex-col p-4 bg-white shadow-xl rounded-xl">
            <ProgressSpinner v-if="appState.is_loading_search_results" class="w-8 h-8"></ProgressSpinner>
            <span v-if="appState.show_loading_bar" class="self-center font-bold text-gray-400">{{ appState.progress_step_title }}</span>
            <div v-if="appState.show_loading_bar" class="mt-2 h-2.5 w-32 self-center rounded-full bg-gray-400/50">
              <div
                class="h-2.5 rounded-full bg-blue-400"
                :style="{ width: (appState.progress * 100).toFixed(0) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- <div
          v-if="!appState.show_loading_bar && !appState.search_result_ids.length && !appState.map_id && !appState.is_loading_search_results"
          class="align-center flex flex-1 flex-col justify-center">
          <div class="mb-6 flex flex-row justify-center">
            <img
              class="h-12"
              :src="appState.organization ? appState.organization.workspace_tool_logo_url : ''" />
          </div>
          <div
            class="mb-2 flex-none text-center pointer-events-auto font-bold text-gray-400"
            v-html="appState.organization ? appState.organization.workspace_tool_intro_text : ''"></div>
        </div> -->
      </div>

    </div>

  </div>

</template>

<style scoped>
</style>
